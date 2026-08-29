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

## Production (Render + Neon + Resend) — Path A

Hosted identity so sign-in works from any Mac. Vault stays local; Cloud Watch can stay local for FYP demos.

### 1. Neon Postgres

1. Create a project at [neon.com](https://neon.com) (free tier, no card).
2. Copy the **pooled** connection string → `DATABASE_URL`.

### 2. Resend email OTP

1. Add and verify your domain at [resend.com](https://resend.com).
2. Create an API key → `RESEND_API_KEY`.
3. Set `RESEND_FROM=Nous <noreply@yourdomain.com>`.

### 3. Secrets

```bash
openssl rand -hex 32   # BETTER_AUTH_SECRET
openssl rand -hex 24   # AUTH_INTERNAL_SECRET (same in repo root .env)
```

Or run from repo root:

```bash
chmod +x scripts/setup_path_a_auth.sh
./scripts/setup_path_a_auth.sh
```

### 4. Render

**Option A — Blueprint:** Push repo to GitHub → Render → New → Blueprint → select repo → uses [`render.yaml`](../render.yaml) at repo root (`rootDir: auth`).

**Option B — Manual web service:**

| Setting | Value |
|---------|--------|
| Root directory | `auth` |
| Build | `npm install && npm run migrate && npm run migrate:devices` |
| Start | `npm start` |
| Health check | `/health` |
| Plan | Free |

Set environment variables from [`.env.production.example`](.env.production.example). **`BETTER_AUTH_URL` must exactly match** `https://<your-service>.onrender.com` (no trailing slash).

### 5. Point Nous at hosted auth

After the first successful deploy:

```bash
./scripts/setup_path_a_auth.sh https://YOUR-SERVICE.onrender.com
```

This updates `desktop/.env` (`VITE_AUTH_URL`) and root `.env` (`AUTH_URL`). Restart the desktop app.

Verify:

```bash
./scripts/verify_hosted_auth.sh
```

### 6. Local Cloud Watch (optional)

If you run `cloud-watch` Docker locally, root `.env` must use the **Render** `AUTH_URL` (not `localhost:3000`) so Bearer sessions resolve. Restart the container after changing env.

### Limitations (free Render)

- Service sleeps after ~15 min idle; first sign-in may take ~30–60s (cold start).
- Cloud Watch / weekday cron is **not** hosted in Path A — briefs still run locally or via manual `curl`.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| * | `/api/auth/*` | Better Auth (email OTP) |
| GET | `/internal/session` | `X-Internal-Secret` + Bearer session |
| POST | `/devices/register` | session cookie or Bearer |
| GET | `/devices/me` | session cookie or Bearer |
| GET | `/health` | none |

Desktop uses `VITE_AUTH_URL` (`desktop/.env`). Production example: `https://nous-auth.onrender.com`. Cloud Watch uses `AUTH_URL` + `AUTH_INTERNAL_SECRET` to resolve Bearer sessions.
