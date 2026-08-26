# Nous Cloud Watch — multi-user v1

Hosted morning briefs for **any Nous user**. You run one Droplet; they sign up in the app and bring their own LLM key (BYOK). Vault stays on their Mac.

## User experience

1. Open Nous → **Sign in** / **Create account** (welcome gate when Cloud Watch is enabled on this build)  
2. Or **Continue without account** for local-only use  
3. Settings → **Models** — add your Groq/OpenRouter key once (same key as Research). Sign-in and Models saves sync it to Cloud Watch automatically.  
4. Activate Watches — briefs run ~9am on the server and sync when they open Nous   

Users never see a service URL, Docker, or crontab.

## Operator: enable sign-in for shipped builds

On each desktop install’s sidecar `.env` (or bake into the release):

```bash
CLOUD_WATCH_URL=https://watch.your-domain.com
```

That URL is **hidden from Settings**. Empty URL → no sign-in gate; local catch-up only.

## Operator deploy (you, once)

### Env on the Droplet

```bash
# Cron-only (keep secret — never give to users)
CLOUD_WATCH_CRON_TOKEN=$(openssl rand -hex 24)
# Encrypts user BYOK keys at rest
CLOUD_WATCH_SECRET=$(openssl rand -hex 32)

# Optional defaults for non-BYOK tooling; users override via BYOK
ENABLE_WEB_SEARCH=true
ENABLE_ARXIV=true
WATCH_MAX_PASSES=1
TAVILY_API_KEY=...   # if web search needs it globally
```

Also put the same values in the repo `.env` that Compose loads, or export them before `docker compose up`.

### Start

From repo root:

```bash
cd cloud-watch && docker compose up --build -d
```

Put HTTPS in front (Caddy/nginx) → `https://watch.your-domain.com`.

### Cron (server local time = user default Asia/Singapore unless you change droplet TZ)

```bash
0 9 * * 1-5 curl -fsS -X POST \
  -H "Authorization: Bearer $CLOUD_WATCH_CRON_TOKEN" \
  http://127.0.0.1:8787/internal/run-due
```

## API

| Method | Path | Auth |
|--------|------|------|
| POST | `/v1/auth/register` | none |
| POST | `/v1/auth/login` | none |
| GET | `/v1/me` | user session |
| PUT | `/v1/me/llm` | user session (BYOK) |
| PUT | `/v1/watches/{id}` | user session |
| GET | `/v1/briefs/pending` | user session |
| POST | `/v1/briefs/{id}/ack` | user session |
| POST | `/internal/run-due` | cron token |

## Local catch-up

If a user never signs in, Nous still runs Watch catch-up **while the app is open**. Cloud is additive.

## Notes

- SQLite under `/data` — fine for FYP / small user counts.  
- One Watch ≈ several LLM calls; free Groq tiers are per-user when they BYOK.  
- Do not put your personal free-tier key as the only server key for all users.
