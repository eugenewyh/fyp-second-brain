#!/usr/bin/env bash
# Start the Second Brain HTTP sidecar (used by Tauri desktop app)
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
export PYTHONPATH=src
exec python sidecar/server.py