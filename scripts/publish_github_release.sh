#!/usr/bin/env bash
# Create a GitHub Release and upload Tauri build artifacts.
# Prerequisite: gh auth login, NOUS_NVIDIA_API_KEY for --build.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(python3 -c "import json; print(json.load(open('desktop/src-tauri/tauri.conf.json'))['version'])")"
TAG="v${VERSION}"
SKIP_BUILD=0
NOTES_FILE=""
DRAFT=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --tag TAG           Git tag (default: v<version> from tauri.conf.json, e.g. v0.1.0)
  --notes-file PATH   Release notes markdown (default: .github/release_notes/<tag>.md or TEMPLATE)
  --skip-build        Do not run package_release.sh; upload existing artifacts only
  --draft             Create a draft release
  -h, --help          Show this help

Examples:
  ./scripts/publish_github_release.sh
  ./scripts/publish_github_release.sh --tag v0.1.0-fyp --skip-build
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      TAG="$2"
      shift 2
      ;;
    --notes-file)
      NOTES_FILE="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD=1
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

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) is required. Install: https://cli.github.com/" >&2
  exit 1
fi

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  echo "==> Building release artifacts..."
  bash "$ROOT/scripts/package_release.sh"
fi

BUNDLE_ROOT="$ROOT/desktop/src-tauri/target/release/bundle"
ASSETS=()

if compgen -G "$BUNDLE_ROOT/dmg/"'*.dmg' >/dev/null; then
  while IFS= read -r -d '' f; do
    ASSETS+=("$f")
  done < <(find "$BUNDLE_ROOT/dmg" -maxdepth 1 -name '*.dmg' -print0 2>/dev/null)
fi

if compgen -G "$BUNDLE_ROOT/nsis/"'*.exe' >/dev/null; then
  while IFS= read -r -d '' f; do
    ASSETS+=("$f")
  done < <(find "$BUNDLE_ROOT/nsis" -maxdepth 1 -name '*.exe' -print0 2>/dev/null)
fi

if [[ ${#ASSETS[@]} -eq 0 ]]; then
  echo "ERROR: No .dmg or .exe artifacts under $BUNDLE_ROOT" >&2
  echo "Run ./scripts/package_release.sh first, or omit --skip-build." >&2
  exit 1
fi

if [[ -z "$NOTES_FILE" ]]; then
  if [[ -f "$ROOT/.github/release_notes/${TAG}.md" ]]; then
    NOTES_FILE="$ROOT/.github/release_notes/${TAG}.md"
  else
    NOTES_FILE="$ROOT/.github/release_notes/TEMPLATE.md"
    echo "NOTE: Using template notes. Add .github/release_notes/${TAG}.md for custom copy."
  fi
fi

if [[ ! -f "$NOTES_FILE" ]]; then
  echo "ERROR: Notes file not found: $NOTES_FILE" >&2
  exit 1
fi

TITLE="Nous ${TAG#v}"
if [[ "$TAG" == *fyp* ]]; then
  TITLE="Nous ${TAG#v} (FYP demo)"
fi

echo "==> Artifacts:"
printf '    %s\n' "${ASSETS[@]}"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "==> Tag $TAG already exists locally."
else
  echo "==> Creating tag $TAG"
  git tag -a "$TAG" -m "Release $TAG"
fi

echo "==> Pushing tag $TAG"
git push github "$TAG"

GH_ARGS=(release create "$TAG" "${ASSETS[@]}" --title "$TITLE" --notes-file "$NOTES_FILE")
if [[ "$DRAFT" -eq 1 ]]; then
  GH_ARGS+=(--draft)
fi

echo "==> Creating GitHub release..."
gh "${GH_ARGS[@]}"

echo ""
echo "Done: https://github.com/eugenewyh/fyp-second-brain/releases/tag/${TAG}"
echo "Latest: https://github.com/eugenewyh/fyp-second-brain/releases/latest"
