#!/usr/bin/env bash
# Detach leftover Tauri/create-dmg volumes and remove rw.*.dmg scratch files.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/desktop/src-tauri/target/release/bundle"

echo "==> Cleaning stale DMG mounts and scratch files..."

if command -v hdiutil >/dev/null 2>&1; then
  # Detach /Volumes/dmg.* (create-dmg mount points).
  for mount in /Volumes/dmg.*; do
    [[ -d "$mount" ]] || continue
    hdiutil detach "$mount" -force 2>/dev/null || true
  done

  # Detach scratch images under our bundle dir.
  while IFS= read -r image_path; do
    [[ -z "$image_path" ]] && continue
    if [[ "$image_path" == *"/desktop/src-tauri/target/release/bundle/"* ]]; then
      hdiutil detach "$image_path" -force 2>/dev/null || true
    fi
  done < <(hdiutil info 2>/dev/null | awk '/image-path/ {print $NF}')
fi

if [[ -d "$BUNDLE" ]]; then
  find "$BUNDLE" -maxdepth 2 -name 'rw.*.dmg' -delete 2>/dev/null || true
fi

echo "==> DMG cleanup done."
