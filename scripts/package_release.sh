#!/usr/bin/env bash
# Full release build: sidecar bundle + tests + Tauri app (macOS / Linux host).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${NOUS_NVIDIA_API_KEY:-}" ]]; then
  if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
  fi
fi

if [[ -z "${NOUS_NVIDIA_API_KEY:-}" ]]; then
  echo "ERROR: NOUS_NVIDIA_API_KEY must be set for release builds."
  echo "Export it or add to .env before running this script."
  exit 1
fi

echo "==> Building sidecar bundle..."
bash "$ROOT/scripts/build_sidecar_bundle.sh"

echo "==> Running tests..."
source "$ROOT/.venv/bin/activate"
PYTHONPATH=src python -m pytest tests/ -q --ignore=tests/test_graph_integration.py

echo "==> Building Tauri desktop app..."
export PATH="/opt/homebrew/bin:$PATH"
cd "$ROOT/desktop"
npm run tauri build

echo ""
echo "==> Build complete!"
echo "    macOS app: desktop/src-tauri/target/release/bundle/macos/"
echo "    .dmg:      desktop/src-tauri/target/release/bundle/dmg/"
echo ""
echo "Smoke test (optional):"
echo "  ./scripts/smoke_release.sh"
