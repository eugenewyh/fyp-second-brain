# Nous Auth — Better Auth + Postgres

Email OTP sign-in for Nous Account. Vault stays local; this service only owns identity, sessions, and device registration.

## Local demo ($0 — your laptop)

Others only reach this while **your Mac is on** and these processes are running (UAT on this machine, or classmates sitting with you).

1. Start **Docker Desktop**, then:

```bash
cd auth
cp -n .env.example .env   # already done if .env exists
docker compose up -d      # Postgres on :5433
npm install
npm run migrate
npm run migrate:devices
npm run dev               # http://localhost:3000 — OTP prints here
```

2. Desktop already expects `VITE_AUTH_URL=http://localhost:3000` (`desktop/.env`). Restart the Vite/Tauri app after changing it.

3. Root `.env` should have `AUTH_URL=http://127.0.0.1:3000` and the same `AUTH_INTERNAL_SECRET` as `auth/.env` (for Cloud Watch). Optional: `cd cloud-watch && docker compose up --build -d`.

4. In the app: **Settings → Account** → email → code from the auth terminal (no Resend needed).

No public hosting. No payment. Sign-in dies when you quit auth / sleep the Mac hard enough to kill Docker.

## Setup (same commands as above)

```bash
cd auth
cp .env.example .env
# Edit BETTER_AUTH_SECRET (≥32 chars), AUTH_INTERNAL_SECRET, DATABASE_URL

docker compose up -d          # local Postgres on :5433
npm install
npm run migrate               # Better Auth tables
npm run migrate:devices       # devices table
npm run dev                   # http://localhost:3000
```

Without `RESEND_API_KEY`, OTPs are printed to the auth server stdout (`AUTH_DEV_LOG_OTP=1`).

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| * | `/api/auth/*` | Better Auth (email OTP) |
| GET | `/internal/session` | `X-Internal-Secret` + Bearer session |
| POST | `/devices/register` | session cookie or Bearer |
| GET | `/devices/me` | session cookie or Bearer |
| GET | `/health` | none |

Desktop uses `VITE_AUTH_URL=http://localhost:3000`. Cloud Watch uses `AUTH_URL` + `AUTH_INTERNAL_SECRET` to resolve Bearer sessions.
