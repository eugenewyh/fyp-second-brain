#!/usr/bin/env bash
# macOS dev runner: build with cargo, then launch from .app so Dock gets the bundle icon.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_DIR="$ROOT/src-tauri"
SYNC="$ROOT/scripts/sync_macos_app_bundle.sh"

cd "$TAURI_DIR"

cmd="${1:-}"
shift || true

if [[ "$cmd" == "run" ]]; then
  cargo_args=()
  app_args=()
  seen_sep=false

  for arg in "$@"; do
    if $seen_sep; then
      app_args+=("$arg")
    elif [[ "$arg" == "--" ]]; then
      seen_sep=true
    else
      cargo_args+=("$arg")
    fi
  done

  cargo build "${cargo_args[@]+"${cargo_args[@]}"}"
  bash "$SYNC"
  exec "$TAURI_DIR/target/debug/bundle/macos/Nous.app/Contents/MacOS/desktop" \
    "${app_args[@]+"${app_args[@]}"}"
fi

exec cargo "$cmd" "$@"
