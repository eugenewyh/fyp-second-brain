from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

from .state import Endpoint, ModelCard
from .store import RunRecord

_ENDPOINT_PROOF = object()


@dataclass(frozen=True, slots=True)
class Serving:
    model: ModelCard


@dataclass(frozen=True, slots=True)
class Loading:
    percent: float | None


@dataclass(frozen=True, slots=True)
class WrongModel:
    served_ids: tuple[str, ...]

    @property
    def serving_id(self) -> str:
        return self.served_ids[0]


@dataclass(frozen=True, slots=True)
class Unreachable:
    detail: str


@dataclass(frozen=True, slots=True)
class Malformed:
    detail: str


@dataclass(frozen=True, slots=True)
class Exited:
    code: int
    detail: str


HealthReport = Serving | Loading | WrongModel | Unreachable | Malformed | Exited


def parse_models_payload(raw: object, *, expect_model: str) -> HealthReport:
    if not isinstance(raw, dict):
        return Malformed(detail="payload is not an object")
    data = raw.get("data")
    if not isinstance(data, list):
        return Malformed(detail="missing data list")
    ids: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            return Malformed(detail="model entry is not an object")
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id:
            return Malformed(detail="model entry missing id")
        ids.append(model_id)
    if not ids:
        return Malformed(detail="data list is empty")
    if expect_model in ids:
        return Serving(
            model=ModelCard(
                id=expect_model,
                display_name=expect_model,
                disk_bytes=0,
                context_window=0,
                active_params_b=0.0,
                total_params_b=0.0,
            )
        )
    return WrongModel(served_ids=tuple(ids))


def mint_endpoint(report: HealthReport, *, base_url: str, token: str) -> Endpoint:
    if not isinstance(report, Serving):
        raise TypeError(f"cannot mint Endpoint from {type(report).__name__}")
    return Endpoint(base_url=base_url, token=token, _proof=_ENDPOINT_PROOF)


def probe(rec: RunRecord, *, expect_model: str, timeout_s: float) -> HealthReport:
    url = f"http://127.0.0.1:{rec.port}/v1/models"
    try:
        req = Request(url, headers={"Authorization": f"Bearer {rec.token}"})
        with urlopen(req, timeout=timeout_s) as resp:
            raw = json.loads(resp.read().decode())
    except json.JSONDecodeError as exc:
        return Malformed(detail=str(exc))
    except (OSError, URLError, TimeoutError) as exc:
        return Unreachable(detail=str(exc))
    return parse_models_payload(raw, expect_model=expect_model)
