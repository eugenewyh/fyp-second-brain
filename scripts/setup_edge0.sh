#!/usr/bin/env bash
# Install / refresh the Edge0 CLI + checkpoint for Nous on-device mode.
# Usage:
#   bash scripts/setup_edge0.sh              # 8B (~4.2 GB)
#   bash scripts/setup_edge0.sh edge0-35b    # 35B (~23 GB)
#
# Progress prints in the terminal. A copy also goes to .edge0/setup-<tier>.log
set -euo pipefail

TIER="${1:-edge0-8b}"
case "$TIER" in
  edge0-8b|8b)
    TIER=edge0-8b
    HF_REPO=Edge0/Edge0-8B-A1B-preview
    SIZE_HINT="~4.2 GB"
    ENV_KEY=EDGE0_8B_MODEL
    ;;
  edge0-35b|35b)
    TIER=edge0-35b
    HF_REPO=Edge0/Edge0-35B-A3B-preview
    SIZE_HINT="~23 GB"
    ENV_KEY=EDGE0_35B_MODEL
    ;;
  *)
    echo "Usage: $0 [edge0-8b|edge0-35b]" >&2
    exit 2
    ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EDGE0_ROOT="$ROOT/.edge0"
RUNTIME="$EDGE0_ROOT/runtime"
MODEL_DIR="$ROOT/local-engine/$TIER"
LOG="$EDGE0_ROOT/setup-${TIER}.log"

mkdir -p "$EDGE0_ROOT" "$ROOT/local-engine"
touch "$LOG"

log() {
  # Show in Terminal and append to the log file.
  printf '%s\n' "$*" | tee -a "$LOG"
}

log "==> $(date -u +%Y-%m-%dT%H:%M:%SZ) Edge0 setup ($TIER) starting"
log "    log file: $LOG"

if [[ ! -d "$EDGE0_ROOT/Edge0/src" ]]; then
  log "==> Fetching Edge0 source"
  curl -fsSL -o "$EDGE0_ROOT/edge0-src.tar.gz" \
    https://github.com/Edge0-AI/Edge0/archive/refs/heads/main.tar.gz
  rm -rf "$EDGE0_ROOT/Edge0"
  tar -xzf "$EDGE0_ROOT/edge0-src.tar.gz" -C "$EDGE0_ROOT"
  mv "$EDGE0_ROOT/Edge0-main" "$EDGE0_ROOT/Edge0"
fi

if [[ ! -x "$RUNTIME/bin/edge0" ]]; then
  log "==> Creating Edge0 venv + installing CLI"
  rm -rf "$RUNTIME"
  python3.12 -m venv --copies "$RUNTIME"
  "$RUNTIME/bin/pip" install -U pip wheel
  "$RUNTIME/bin/pip" install -e "$EDGE0_ROOT/Edge0[fetch]"
fi

# Stale locks from an interrupted download make hf hang with no progress.
if [[ -d "$MODEL_DIR/.cache" ]]; then
  find "$MODEL_DIR/.cache" -name '*.lock' -delete 2>/dev/null || true
fi

log "==> Downloading $HF_REPO ($SIZE_HINT) → $MODEL_DIR"
log "    (safe to re-run; resumes incomplete files)"
# Keep HF progress on the real terminal (not swallowed by the log).
set +e
"$RUNTIME/bin/hf" download "$HF_REPO" --local-dir "$MODEL_DIR" 2>&1 | tee -a "$LOG"
hf_status=${PIPESTATUS[0]}
set -e
if [[ "$hf_status" -ne 0 ]]; then
  log "ERROR: download failed (exit $hf_status). Re-run the same command to resume."
  exit "$hf_status"
fi

if [[ ! -f "$MODEL_DIR/config.json" ]]; then
  log "ERROR: config.json missing under $MODEL_DIR"
  exit 1
fi
# 8b ships model.safetensors; 35b ships model-0000N-of-0000M.safetensors.
if ! compgen -G "$MODEL_DIR/model*.safetensors" >/dev/null; then
  log "ERROR: weight files missing under $MODEL_DIR (download incomplete)."
  log "       Re-run: bash scripts/setup_edge0.sh $TIER"
  exit 1
fi

ENV_FILE="$ROOT/.env"
touch "$ENV_FILE"
python3 - "$ENV_FILE" "$RUNTIME/bin/edge0" "$ENV_KEY" "$MODEL_DIR" "$TIER" <<'PY' | tee -a "$LOG"
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
cli, env_key, model, tier = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
wanted = {
    "LOCAL_ENGINE_RUNTIME": "edge0",
    "LOCAL_ENGINE_MODEL": tier,
    "LOCAL_ENGINE_START_TIMEOUT_S": "600",
    "EDGE0_CLI": cli,
    env_key: model,
}
lines = env_path.read_text().splitlines() if env_path.exists() else []
seen = set()
out = []
for line in lines:
    if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
        out.append(line)
        continue
    key, _, _ = line.partition("=")
    if key in wanted:
        out.append(f"{key}={wanted[key]}")
        seen.add(key)
    else:
        out.append(line)
for key, value in wanted.items():
    if key not in seen:
        out.append(f"{key}={value}")
env_path.write_text("\n".join(out) + "\n")
print(f"==> Wrote {', '.join(wanted)} into {env_path}")
PY

log "==> Smoke: edge0 models"
"$RUNTIME/bin/edge0" models 2>&1 | tee -a "$LOG" || true

log "==> Done. Restart the Nous sidecar, then Settings → Models → On-device → Start → Use."
log "    CLI:   $RUNTIME/bin/edge0"
log "    Tier:  $TIER"
log "    Model: $MODEL_DIR"
du -sh "$MODEL_DIR" | tee -a "$LOG"
log "SETUP_EDGE0_OK"
