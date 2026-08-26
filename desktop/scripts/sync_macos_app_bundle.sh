#!/usr/bin/env bash
# Keep macOS .app bundles in sync with the latest debug binary and icon.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_DIR="$ROOT/src-tauri"
BIN="$TAURI_DIR/target/debug/desktop"
ICNS="$TAURI_DIR/icons/icon.icns"
APP="$TAURI_DIR/target/debug/bundle/macos/Nous.app"
DEV_APP="$ROOT/Nous.dev.app"
STAMP="$(date +%s)"

if [[ ! -f "$BIN" ]]; then
  echo "sync_macos_app_bundle: no debug binary yet ($BIN)"
  exit 0
fi

if [[ ! -f "$ICNS" ]]; then
  echo "sync_macos_app_bundle: missing icon at $ICNS"
  exit 1
fi

write_info_plist() {
  local plist="$1"
  local executable="$2"
  local icon_file="$3"
  local identifier="$4"

  cat >"$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>English</string>
  <key>CFBundleDisplayName</key>
  <string>Nous</string>
  <key>CFBundleExecutable</key>
  <string>${executable}</string>
  <key>CFBundleIdentifier</key>
  <string>${identifier}</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>Nous</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleVersion</key>
  <string>${STAMP}</string>
  <key>CFBundleIconFile</key>
  <string>${icon_file}</string>
  <key>CSResourcesFileMapped</key>
  <true/>
  <key>LSMinimumSystemVersion</key>
  <string>10.13</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF
}

sync_bundle() {
  local app_dir="$1"
  local executable="$2"
  local icon_name="$3"
  local icon_dest="$4"
  local identifier="$5"

  mkdir -p "$app_dir/Contents/MacOS" "$app_dir/Contents/Resources"
  cp "$BIN" "$app_dir/Contents/MacOS/$executable"
  chmod +x "$app_dir/Contents/MacOS/$executable"
  cp "$ICNS" "$icon_dest"
  write_info_plist "$app_dir/Contents/Info.plist" "$executable" "$icon_name" "$identifier"
  touch "$app_dir" "$app_dir/Contents/Info.plist"
}

sync_bundle "$APP" "desktop" "icon" "$APP/Contents/Resources/icon.icns" "com.tp068819.nous"
sync_bundle "$DEV_APP" "Nous" "AppIcon" "$DEV_APP/Contents/Resources/AppIcon.icns" "com.tp068819.nous.dev"

LS=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
if [[ -x "$LS" ]]; then
  "$LS" -f "$APP" >/dev/null 2>&1 || true
  "$LS" -f "$DEV_APP" >/dev/null 2>&1 || true
fi

echo "sync_macos_app_bundle: synced binary + icon (CFBundleVersion=$STAMP)"
