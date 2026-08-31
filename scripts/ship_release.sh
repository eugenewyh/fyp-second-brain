#!/usr/bin/env bash
# One-command maintainer release: bump version → build → GitHub Release.
#
# Typical use after merging fixes:
#   ./scripts/ship_release.sh
#
# Rebuild and replace the current release (same version, new .dmg):
#   ./scripts/ship_release.sh --replace --no-bump
#
# Prerequisite: gh auth login, NOUS_NVIDIA_API_KEY in env or .env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUMP="patch"
EXPLICIT_VERSION=""
NO_BUMP=0
REPLACE=0
SKIP_TESTS=0
DRAFT=0
NOTES_FILE=""
MESSAGE=""

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  Default: bump patch version, build, tag, publish to GitHub Releases.

Options:
  --bump patch|minor|major   Version bump when not using --version (default: patch)
  --version X.Y.Z            Set an exact semver (overrides --bump)
  --no-bump                  Keep version in tauri.conf.json (use with --replace)
  --replace                  Re-upload assets to an existing release tag
  --message TEXT             One-line release notes (creates .github/release_notes/<tag>.md)
  --notes-file PATH          Use custom release notes markdown
  --skip-tests               Skip pytest during build
  --draft                    Create a draft GitHub release
  -h, --help                 Show this help

Examples:
  ./scripts/ship_release.sh
  ./scripts/ship_release.sh --message "Fix routing on empty topics"
  ./scripts/ship_release.sh --replace --no-bump --skip-tests
  ./scripts/ship_release.sh --version 0.2.0 --message "Research auto-escalation"
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bump)
      BUMP="$2"
      shift 2
      ;;
    --version)
      EXPLICIT_VERSION="$2"
      shift 2
      ;;
    --no-bump)
      NO_BUMP=1
      shift
      ;;
    --replace)
      REPLACE=1
      shift
      ;;
    --message)
      MESSAGE="$2"
      shift 2
      ;;
    --notes-file)
      NOTES_FILE="$2"
      shift 2
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    --draft)
      DRAFT=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$BUMP" != "patch" && "$BUMP" != "minor" && "$BUMP" != "major" ]]; then
  echo "ERROR: --bump must be patch, minor, or major" >&2
  exit 1
fi

read_version() {
  python3 -c "import json; print(json.load(open('$ROOT/desktop/src-tauri/tauri.conf.json'))['version'])"
}

bump_version() {
  local current="$1"
  python3 - "$current" "$BUMP" "$EXPLICIT_VERSION" <<'PY'
import re
import sys

current, bump, explicit = sys.argv[1:4]
if explicit:
    if not re.fullmatch(r"\d+\.\d+\.\d+", explicit):
        sys.exit("Version must be semver X.Y.Z")
    print(explicit)
    sys.exit(0)

parts = [int(x) for x in current.split(".")]
while len(parts) < 3:
    parts.append(0)
major, minor, patch = parts[:3]
if bump == "major":
    major += 1
    minor = 0
    patch = 0
elif bump == "minor":
    minor += 1
    patch = 0
else:
    patch += 1
print(f"{major}.{minor}.{patch}")
PY
}

write_version() {
  local version="$1"
  ROOT="$ROOT" VERSION="$version" python3 <<'PY'
import json
import os
import re
from pathlib import Path

version = os.environ["VERSION"]
root = Path(os.environ["ROOT"])

tauri_conf = root / "desktop/src-tauri/tauri.conf.json"
data = json.loads(tauri_conf.read_text(encoding="utf-8"))
data["version"] = version
tauri_conf.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

cargo = root / "desktop/src-tauri/Cargo.toml"
cargo_text = cargo.read_text(encoding="utf-8")
cargo.write_text(
    re.sub(r'^version = "[^"]+"', f'version = "{version}"', cargo_text, count=1, flags=re.M),
    encoding="utf-8",
)

pkg = root / "desktop/package.json"
pkg_data = json.loads(pkg.read_text(encoding="utf-8"))
pkg_data["version"] = version
pkg.write_text(json.dumps(pkg_data, indent=2) + "\n", encoding="utf-8")
PY
}

CURRENT="$(read_version)"
if [[ "$NO_BUMP" -eq 1 ]]; then
  NEXT="$CURRENT"
  echo "==> Keeping version $NEXT"
else
  NEXT="$(bump_version "$CURRENT")"
  echo "==> Bumping version $CURRENT → $NEXT"
  write_version "$NEXT"
fi

TAG="v${NEXT}"
NOTES_PATH="$ROOT/.github/release_notes/${TAG}.md"

if [[ -n "$NOTES_FILE" ]]; then
  :
elif [[ -f "$NOTES_PATH" ]]; then
  NOTES_FILE="$NOTES_PATH"
elif [[ -n "$MESSAGE" ]]; then
  mkdir -p "$ROOT/.github/release_notes"
  cat >"$NOTES_PATH" <<EOF
## Nous ${NEXT}

${MESSAGE}

### Download

Open [Releases](https://github.com/eugenewyh/fyp-second-brain/releases/latest) and download the \`.dmg\` (macOS) or \`.exe\` (Windows) for your platform.

User data is preserved when you replace the app — it lives in Application Support, not inside the bundle.
EOF
  NOTES_FILE="$NOTES_PATH"
  echo "==> Wrote release notes: $NOTES_PATH"
else
  echo "TIP: Pass --message \"…\" for custom release notes (otherwise uses TEMPLATE.md)."
fi

PUBLISH_ARGS=(--tag "$TAG")
[[ "$REPLACE" -eq 1 ]] && PUBLISH_ARGS+=(--replace)
[[ "$SKIP_TESTS" -eq 1 ]] && PUBLISH_ARGS+=(--skip-tests)
[[ "$DRAFT" -eq 1 ]] && PUBLISH_ARGS+=(--draft)
[[ -n "$NOTES_FILE" ]] && PUBLISH_ARGS+=(--notes-file "$NOTES_FILE")

echo "==> Publishing $TAG..."
bash "$ROOT/scripts/publish_github_release.sh" "${PUBLISH_ARGS[@]}"

echo ""
echo "Shipped $TAG."
if [[ "$NO_BUMP" -eq 0 && "$NEXT" != "$CURRENT" ]]; then
  echo "Version files updated — commit when ready:"
  echo "  git add desktop/src-tauri/tauri.conf.json desktop/src-tauri/Cargo.toml desktop/package.json"
  [[ -f "$NOTES_PATH" ]] && echo "  git add .github/release_notes/${TAG}.md"
  echo "  git commit -m \"chore: release ${TAG}\""
fi
