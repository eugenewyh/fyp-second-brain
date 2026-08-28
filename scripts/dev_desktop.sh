#!/usr/bin/env bash
# One command for local demos: auth (+ optional Cloud Watch) then Tauri.
#
#   ./scripts/dev_desktop.sh
#
# Tauri already starts the Python sidecar. You only need this so Account OTP works.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUTH_PID=""
CW_PID=""

cleanup() {
  if [[ -n "${AUTH_PID}" ]] && kill -0 "${AUTH_PID}" 2>/dev/null; then
    echo "Stopping auth (pid ${AUTH_PID})…"
    kill "${AUTH_PID}" 2>/dev/null || true
  fi
  if [[ -n "${CW_PID}" ]] && kill -0 "${CW_PID}" 2>/dev/null; then
    echo "Stopping cloud-watch (pid ${CW_PID})…"
    kill "${CW_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

auth_up() {
  curl -fsS --max-time 1 "http://127.0.0.1:3000/health" >/dev/null 2>&1
}

ensure_auth() {
  if auth_up; then
    echo "Auth already running on :3000"
    return
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "Docker Desktop is not running."
    echo "Open it, wait until ready, then re-run: ./scripts/dev_desktop.sh"
    echo "Or skip Account OTP and run only: cd desktop && npm run tauri dev"
    exit 1
  fi

  cd "$ROOT/auth"
  [[ -f .env ]] || cp .env.example .env
  docker compose up -d
  for _ in $(seq 1 40); do
    if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
  npm install --silent
  npm run migrate
  npm run migrate:devices

  echo "Starting auth on http://localhost:3000 (OTP codes print below if Resend unset)…"
  npm run dev >"$ROOT/.auth-dev.log" 2>&1 &
  AUTH_PID=$!
  for _ in $(seq 1 40); do
    if auth_up; then
      echo "Auth ready. Logs: $ROOT/.auth-dev.log"
      return
    fi
    sleep 0.5
  done
  echo "Auth failed to start. Last log lines:"
  tail -n 40 "$ROOT/.auth-dev.log" || true
  exit 1
}

ensure_cloud_watch() {
  [[ "${DEV_CLOUD_WATCH:-0}" == "1" ]] || return 0
  if curl -fsS --max-time 1 "http://127.0.0.1:8787/health" >/dev/null 2>&1; then
    echo "Cloud Watch already running on :8787"
    return
  fi
  if [[ ! -d "$ROOT/cloud-watch" ]]; then
    return
  fi
  echo "Starting Cloud Watch (DEV_CLOUD_WATCH=1)…"
  cd "$ROOT/cloud-watch"
  if [[ -f docker-compose.yml ]] && docker info >/dev/null 2>&1; then
    docker compose up --build -d || true
  fi
}

echo "==> Auth"
ensure_auth
echo "==> Cloud Watch (optional)"
ensure_cloud_watch
echo "==> Desktop (Vite + Tauri + sidecar)"
cd "$ROOT/desktop"
if [[ ! -f .env ]] || ! grep -q 'VITE_AUTH_URL' .env 2>/dev/null; then
  echo 'VITE_AUTH_URL=http://localhost:3000' > .env
  echo "Wrote desktop/.env with VITE_AUTH_URL"
fi
exec npm run tauri dev
