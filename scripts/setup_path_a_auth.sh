#!/usr/bin/env bash
# Path A — generate secrets and wire local .env files to a hosted Render auth URL.
#
# Usage:
#   ./scripts/setup_path_a_auth.sh                    # print secrets + checklist
#   ./scripts/setup_path_a_auth.sh https://nous-auth.onrender.com
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RENDER_URL="${1:-}"

gen_secret() {
  openssl rand -hex "$1"
}

patch_env() {
  local file="$1"
  local key="$2"
  local val="$3"
  touch "$file"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    if [[ "$(uname)" == Darwin ]]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" "$file"
    else
      sed -i "s|^${key}=.*|${key}=${val}|" "$file"
    fi
  else
    echo "${key}=${val}" >> "$file"
  fi
}

echo "==> Path A hosted auth setup"
echo ""

if [[ -z "${RENDER_URL}" ]]; then
  echo "Generated secrets (save for Neon/Resend/Render — also put in auth/.env for local migrate):"
  echo ""
  echo "BETTER_AUTH_SECRET=$(gen_secret 32)"
  echo "AUTH_INTERNAL_SECRET=$(gen_secret 24)"
  echo ""
  echo "Checklist:"
  echo "  1. Neon  → https://neon.com — create project, copy pooled DATABASE_URL"
  echo "  2. Resend → https://resend.com — verify domain, create API key"
  echo "  3. Render → New Web Service OR Blueprint from render.yaml"
  echo "     - Root directory: auth"
  echo "     - Build: npm install && npm run migrate && npm run migrate:devices"
  echo "     - Start: npm start"
  echo "     - Health: /health"
  echo "  4. Set env vars from auth/.env.production.example on Render"
  echo "  5. Re-run: ./scripts/setup_path_a_auth.sh https://YOUR-SERVICE.onrender.com"
  echo ""
  exit 0
fi

RENDER_URL="${RENDER_URL%/}"
echo "Using auth URL: ${RENDER_URL}"

patch_env "$ROOT/.env" "AUTH_URL" "${RENDER_URL}"
patch_env "$ROOT/desktop/.env" "VITE_AUTH_URL" "${RENDER_URL}"

if ! grep -q '^AUTH_INTERNAL_SECRET=.\+' "$ROOT/.env" 2>/dev/null; then
  echo ""
  echo "WARN: Set AUTH_INTERNAL_SECRET in $ROOT/.env to the same value as on Render."
fi

echo ""
echo "Updated:"
echo "  $ROOT/.env (AUTH_URL)"
echo "  $ROOT/desktop/.env (VITE_AUTH_URL)"
echo ""
echo "If local Cloud Watch Docker is running, restart it so AUTH_URL reaches Render:"
echo "  docker compose -f cloud-watch/docker-compose.yml --env-file .env up -d --force-recreate"
echo ""
echo "Restart Nous desktop (npm run tauri dev) then test Settings → Account."
echo ""
echo "Health check:"
curl -fsS "${RENDER_URL}/health" && echo "" || echo "  (service not up yet — wait for Render deploy)"
