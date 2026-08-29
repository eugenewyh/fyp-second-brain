#!/usr/bin/env bash
# Verify hosted auth is reachable. Reads VITE_AUTH_URL from desktop/.env or pass URL as arg.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
URL="${1:-}"

if [[ -z "$URL" ]] && [[ -f "$ROOT/desktop/.env" ]]; then
  URL="$(grep '^VITE_AUTH_URL=' "$ROOT/desktop/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
URL="${URL%/}"

if [[ -z "$URL" ]] || [[ "$URL" == *localhost* ]]; then
  echo "No hosted auth URL. Set desktop/.env VITE_AUTH_URL or pass URL as argument."
  exit 1
fi

echo "Checking ${URL}/health ..."
if ! body="$(curl -fsS "${URL}/health")"; then
  echo "FAIL — service not reachable (deploy Render first?)"
  exit 1
fi
echo "$body" | python3 -m json.tool
echo "OK — hosted auth is up."
