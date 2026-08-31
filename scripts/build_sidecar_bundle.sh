#!/usr/bin/env bash
# Build the Python sidecar bundle for Tauri release (macOS / Linux builders).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/desktop/src-tauri/sidecar-bundle"
REQ="$ROOT/requirements.txt"
PYTHON="${PYTHON:-python3.12}"

if [[ ! -f "$REQ" ]]; then
  echo "Missing requirements.txt at $REQ"
  exit 1
fi

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
  echo "NOUS_NVIDIA_API_KEY is required for release builds (Nous-included NVIDIA access)."
  echo "Export it or add to .env before running package_release.sh"
  exit 1
fi

echo "==> Cleaning sidecar bundle at $BUNDLE"
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE"

echo "==> Creating venv ($PYTHON)"
"$PYTHON" -m venv "$BUNDLE/venv"
# shellcheck disable=SC1091
source "$BUNDLE/venv/bin/activate"
pip install --upgrade pip wheel
pip install -r "$REQ"

echo "==> Copying application code"
cp -R "$ROOT/src" "$BUNDLE/src"
cp -R "$ROOT/sidecar" "$BUNDLE/sidecar"
mkdir -p "$BUNDLE/data"
cp -R "$ROOT/data/job_router" "$BUNDLE/data/job_router"

echo "==> Pre-caching fastembed model"
export FASTEMBED_CACHE_PATH="$BUNDLE/fastembed_cache"
mkdir -p "$FASTEMBED_CACHE_PATH"
python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

echo "==> Writing operator.env (build-time secrets)"
cat >"$BUNDLE/operator.env" <<EOF
LLM_PROVIDER=nvidia
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b
LLM_FALLBACK_MODEL=nvidia/nemotron-3-nano-30b-a3b
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
NOUS_NVIDIA_API_KEY=${NOUS_NVIDIA_API_KEY}
EOF
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  echo "GEMINI_API_KEY=${GEMINI_API_KEY}" >>"$BUNDLE/operator.env"
fi
if [[ -n "${TAVILY_API_KEY:-}" ]]; then
  echo "TAVILY_API_KEY=${TAVILY_API_KEY}" >>"$BUNDLE/operator.env"
fi

deactivate 2>/dev/null || true

echo "==> Sidecar bundle ready: $BUNDLE"
du -sh "$BUNDLE" || true
