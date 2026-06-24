#!/usr/bin/env bash
# Build Second Brain desktop app for distribution (macOS)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Running tests..."
source .venv/bin/activate
PYTHONPATH=src python -m pytest tests/ -q --ignore=tests/test_graph_integration.py

echo "==> Building Tauri desktop app..."
export PATH="/opt/homebrew/bin:$PATH"
cd desktop
npm run tauri build

echo ""
echo "==> Build complete!"
echo "    macOS app: desktop/src-tauri/target/release/bundle/macos/"
echo "    .dmg:      desktop/src-tauri/target/release/bundle/dmg/"
echo ""
echo "Before distributing, ensure:"
echo "  - Ollama is installed on target machine"
echo "  - Models pulled: nomic-embed-text, llama3.2:3b"
echo "  - User copies .env.example to .env and configures API keys"