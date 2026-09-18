from __future__ import annotations

import hashlib
import os
import platform
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..health import Exited, HealthReport, Serving, WrongModel, probe
from ..state import ModelCard, Progress
from ..store import (
    Artifact,
    InstallPlan,
    RunRecord,
    download_artifacts,
    home,
    is_http_url,
    layout_path,
    materialize_layout,
)
from . import Capability, Refused, Unavailable

CLI_ENV = "EDGE0_CLI"
_GB = 1024**3


@dataclass(frozen=True, slots=True)
class Host:
    os: str
    arch: str
    ram_bytes: int


@dataclass(frozen=True, slots=True)
class Edge0Tier:
    card: ModelCard
    cli_arg: str
    served_id: str
    checkpoint_env: str
    home_dirname: str
    min_ram_bytes: int


@dataclass(frozen=True, slots=True)
class Checkpoint:
    tier: Edge0Tier
    path: Path


@dataclass(frozen=True, slots=True)
class Child:
    proc: subprocess.Popen[bytes]
    log_path: Path


def _card(model_id: str, *, disk_bytes: int) -> ModelCard:
    return ModelCard(
        id=model_id,
        display_name=model_id,
        disk_bytes=disk_bytes,
        context_window=0,
        active_params_b=0.0,
        total_params_b=0.0,
    )


EDGE0_8B = Edge0Tier(
    card=_card("edge0-8b", disk_bytes=4_200_000_000),
    cli_arg="edge0-8b",
    served_id="edge0-8b",
    checkpoint_env="EDGE0_8B_MODEL",
    home_dirname="edge0-8b",
    min_ram_bytes=16 * _GB,
)

EDGE0_35B = Edge0Tier(
    card=_card("edge0-35b", disk_bytes=23_000_000_000),
    cli_arg="edge0-35b",
    served_id="edge0-35b",
    checkpoint_env="EDGE0_35B_MODEL",
    home_dirname="edge0-35b",
    min_ram_bytes=32 * _GB,
)

TIERS: tuple[Edge0Tier, ...] = (EDGE0_8B, EDGE0_35B)

_children: dict[int, Child] = {}
_test_artifacts: dict[str, tuple[Artifact, ...]] = {}


def install_test_catalog(model_id: str, artifacts: tuple[Artifact, ...]) -> None:
    """Point a tier at artifacts a test serves itself. Production never calls this."""
    _test_artifacts[model_id] = artifacts


def clear_test_catalog() -> None:
    _test_artifacts.clear()


def _cli() -> str:
    return (os.getenv(CLI_ENV) or "").strip() or "edge0"


def _host() -> Host:
    return Host(
        os=platform.system(),
        arch=platform.machine(),
        ram_bytes=os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
    )


def _tier_for(model_id: str) -> Edge0Tier:
    for tier in TIERS:
        if tier.card.id == model_id:
            return tier
    raise KeyError(model_id)


def capability_for(host: Host, cli: str | None) -> Capability:
    if host.os != "Darwin":
        return Refused(
            reason="os",
            detail="Edge0 runs on macOS only. Use a cloud provider on this machine.",
        )
    if host.arch not in ("arm64", "aarch64"):
        return Refused(
            reason="arch",
            detail="Edge0 needs an Apple silicon Mac. This one is Intel.",
        )
    need = TIERS[0].min_ram_bytes
    if host.ram_bytes < need:
        return Refused(
            reason="memory",
            detail=f"Edge0 needs at least {need // _GB} GB of memory to run {TIERS[0].card.id}.",
        )
    if cli is None:
        return Unavailable(
            detail=f"The edge0 command was not found. Install it, or set {CLI_ENV} "
            "to its full path, then try again.",
        )
    return "ok"


def resolve_checkpoint(tier: Edge0Tier) -> Checkpoint | None:
    raw = (os.getenv(tier.checkpoint_env) or "").strip()
    candidates = [Path(raw).expanduser()] if raw else []
    candidates.append(home() / tier.home_dirname)
    candidates.append(layout_path(tier.card.id))
    for path in candidates:
        if (path / "config.json").is_file():
            return Checkpoint(tier=tier, path=path.resolve())
    return None


def _pending_artifacts(tier: Edge0Tier) -> tuple[Artifact, ...]:
    """What the card offers to download when no checkpoint is on disk yet.

    The url has no http scheme, so acquire refuses it and asks the operator for a
    checkpoint. Pinned per-file shas replace this row once they exist.
    """
    return (
        Artifact(
            name=f"{tier.cli_arg}-checkpoint",
            sha256=hashlib.sha256(tier.cli_arg.encode()).hexdigest(),
            size_bytes=tier.card.disk_bytes,
            url=f"edge0://{tier.cli_arg}",
        ),
    )


def _collect(pid: int) -> bool:
    """True when pid was a child of this process and has now been reaped.

    A pid we spawned but no longer hold a Popen for lingers as a zombie, and a
    zombie still answers signal 0. Reaping it first keeps _pid_alive honest.
    """
    try:
        reaped, _status = os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, OSError):
        return False
    return reaped == pid


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_group(pid: int, sig: int) -> bool:
    # spawn starts a new session, so a pid we own always leads its own group.
    # killpg refuses a reused pid that leads nothing, which is the guard we want.
    try:
        os.killpg(pid, sig)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def _wait_gone(pid: int, *, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        _collect(pid)
        if not _pid_alive(pid):
            return True
        time.sleep(0.05)
    return False


def _terminate_group(pid: int) -> None:
    if not _signal_group(pid, signal.SIGTERM):
        _collect(pid)
        return
    if _wait_gone(pid, timeout_s=10.0):
        return
    _signal_group(pid, signal.SIGKILL)
    _wait_gone(pid, timeout_s=5.0)


def _log_tail(path: Path, *, limit: int = 400) -> str:
    try:
        raw = path.read_bytes()[-4096:].decode(errors="replace")
    except OSError:
        return ""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return lines[-1][:limit] if lines else ""


class Edge0Runtime:
    name = "edge0"
    version = "0"

    def capability(self) -> Capability:
        return capability_for(_host(), shutil.which(_cli()))

    def catalog(self) -> tuple[ModelCard, ...]:
        return tuple(tier.card for tier in TIERS)

    def artifacts(self, model: ModelCard) -> tuple[Artifact, ...]:
        tier = _tier_for(model.id)
        injected = _test_artifacts.get(tier.card.id)
        if injected is not None:
            return injected
        if resolve_checkpoint(tier) is not None:
            return ()
        return _pending_artifacts(tier)

    def acquire(
        self,
        plan: InstallPlan,
        on_progress: Callable[[Progress], None],
        *,
        cancel: threading.Event,
    ) -> None:
        tier = _tier_for(plan.model.id)
        if not plan.missing:
            return
        # Read the catalog once. The layout we are about to write would otherwise
        # change the answer between the download and the materialize.
        wanted = self.artifacts(plan.model)
        if not all(is_http_url(a.url) for a in plan.missing):
            raise RuntimeError(
                f"no {tier.card.id} checkpoint on disk. Point {tier.checkpoint_env} at a "
                f"checkpoint directory, or put one at {home() / tier.home_dirname}."
            )
        download_artifacts(plan, on_progress, cancel=cancel)
        materialize_layout(tier.card.id, wanted)

    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int:
        del token  # edge0 serve has no auth flag; the loopback bind is the boundary
        tier = _tier_for(model.id)
        checkpoint = resolve_checkpoint(tier)
        if checkpoint is None:
            raise RuntimeError(
                f"no {tier.card.id} checkpoint on disk. Set {tier.checkpoint_env}."
            )
        log_dir = home / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"edge0-{port}.log"
        with log_path.open("ab") as log:
            proc = subprocess.Popen(
                [
                    _cli(),
                    "serve",
                    str(checkpoint.path),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        _children[proc.pid] = Child(proc=proc, log_path=log_path)
        return proc.pid

    def health(
        self,
        rec: RunRecord,
        *,
        expect_model: str,
        timeout_s: float,
    ) -> HealthReport:
        child = _children.get(rec.pid)
        if child is not None:
            code = child.proc.poll()
            if code is not None:
                return Exited(code=code, detail=_log_tail(child.log_path))
        tier = _tier_for(expect_model)
        report = probe(rec, expect_model=tier.served_id, timeout_s=timeout_s)
        if isinstance(report, WrongModel) and len(report.served_ids) == 1:
            # We launched this checkpoint ourselves, so a server reporting exactly one
            # model is serving it under whatever id upstream chose.
            live = report.served_ids[0]
            return Serving(model=_card(live, disk_bytes=tier.card.disk_bytes))
        return report

    def terminate(self, pid: int) -> None:
        child = _children.pop(pid, None)
        if child is None:
            _terminate_group(pid)
            return
        proc = child.proc
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        proc.wait()

    def is_alive(self, pid: int) -> bool:
        child = _children.get(pid)
        if child is not None:
            return child.proc.poll() is None
        if _collect(pid):
            return False
        return _pid_alive(pid)


runtime = Edge0Runtime()
