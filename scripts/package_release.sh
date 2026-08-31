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

NOUS_NVIDIA_API_KEY="${NOUS_NVIDIA_API_KEY:-${NVIDIA_API_KEY:-${LLM_API_KEY:-}}}"

if [[ -z "${NOUS_NVIDIA_API_KEY:-}" ]]; then
  echo "ERROR: NOUS_NVIDIA_API_KEY must be set for release builds."
  echo "Export it or add to .env before running this script."
  exit 1
fi

echo "==> Building sidecar bundle..."
bash "$ROOT/scripts/build_sidecar_bundle.sh"

if [[ "${SKIP_TESTS:-0}" == "1" ]]; then
  echo "==> Skipping tests (SKIP_TESTS=1)"
else
  echo "==> Running release smoke tests..."
  source "$ROOT/.venv/bin/activate"
  # Fast, offline subset — full suite can hang on Chroma locks (Nous running) or network tests.
  PYTHONPATH=src python -m pytest \
    tests/test_hybrid_retrieval.py \
    tests/test_ingestion.py \
    tests/test_embeddings_provider.py \
    tests/test_agents.py \
    tests/test_chat.py \
    tests/test_scope.py \
    -q
fi

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
