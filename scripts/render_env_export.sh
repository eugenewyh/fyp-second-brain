#!/usr/bin/env bash
# Print Render environment variables from auth/.env.production.local for dashboard copy-paste.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILE="$ROOT/auth/.env.production.local"

if [[ ! -f "$FILE" ]]; then
  echo "Missing $FILE — run: ./scripts/setup_path_a_auth.sh"
  exit 1
fi

echo "Paste these into Render → nous-auth → Environment (fill empty DATABASE_URL / RESEND first):"
echo ""
grep -v '^#' "$FILE" | grep -v '^$' || true
echo ""
echo "After deploy, set BETTER_AUTH_URL to your actual *.onrender.com URL and redeploy once."
