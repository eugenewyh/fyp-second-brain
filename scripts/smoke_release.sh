#!/usr/bin/env bash
# Smoke-test the sidecar bundle without installing the full .app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/desktop/src-tauri/sidecar-bundle"
PORT="${SIDECAR_PORT:-8766}"
DATA_DIR="$(mktemp -d)"
PID=""

cleanup() {
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
  rm -rf "$DATA_DIR"
}
trap cleanup EXIT

if [[ ! -f "$BUNDLE/sidecar/server.py" ]]; then
  echo "Missing sidecar bundle. Run: ./scripts/build_sidecar_bundle.sh"
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  PYTHON="$BUNDLE/venv/bin/python"
else
  PYTHON="$BUNDLE/venv/bin/python"
  if [[ ! -x "$PYTHON" ]] && [[ -x "$BUNDLE/venv/Scripts/python.exe" ]]; then
    PYTHON="$BUNDLE/venv/Scripts/python.exe"
  fi
fi

export NOUS_BUNDLE_ROOT="$BUNDLE"
export NOUS_DATA_DIR="$DATA_DIR"
export FASTEMBED_CACHE_PATH="$BUNDLE/fastembed_cache"
export SIDECAR_PORT="$PORT"

echo "==> Starting sidecar from bundle (port $PORT)..."
cd "$BUNDLE"
PYTHONPATH="$BUNDLE/src" "$PYTHON" sidecar/server.py &
PID=$!

for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "==> /health"
curl -fsS "http://127.0.0.1:$PORT/health" | python3 -m json.tool

echo "==> /api/settings"
SETTINGS=$(curl -fsS "http://127.0.0.1:$PORT/api/settings")
echo "$SETTINGS" | python3 -m json.tool

python3 - <<'PY' "$SETTINGS"
import json, sys
d = json.loads(sys.argv[1])
assert d.get("llm_configured") is True, "llm_configured should be true"
assert d.get("llm_bundled") is True, "llm_bundled should be true"
assert d.get("connected_providers", {}).get("nvidia") is True
print("OK: llm_configured, llm_bundled, nvidia connected")
PY

echo "==> Smoke test passed"
