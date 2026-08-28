#!/usr/bin/env bash
# Start local Nous Auth (Better Auth + Postgres) for laptop demos.
# Run from anywhere: ./scripts/start_auth.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/auth"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Open Docker Desktop, wait until it’s ready, then re-run:"
  echo "  $ROOT/scripts/start_auth.sh"
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created auth/.env from .env.example — check secrets if needed."
fi

echo "Starting Postgres (auth/docker-compose)…"
docker compose up -d

echo "Waiting for Postgres…"
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Migrating Better Auth + devices…"
npm install --silent
npm run migrate
npm run migrate:devices

echo "Auth API on http://localhost:3000 (OTP codes print in this terminal)"
exec npm run dev
