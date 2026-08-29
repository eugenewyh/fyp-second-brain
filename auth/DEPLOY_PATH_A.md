# Path A deploy checklist (Neon + Resend + Render)

One-time operator steps. Repo side is ready (`render.yaml`, scripts, auth production docs).

## 1. Neon

1. [neon.com](https://neon.com) → New project
2. Copy **pooled** connection string
3. Paste into `auth/.env.production.local` as `DATABASE_URL`

## 2. Resend

1. [resend.com](https://resend.com) → verify your domain
2. Create API key → `RESEND_API_KEY`
3. Set `RESEND_FROM=Nous <noreply@yourdomain.com>`

## 3. Render

1. Push this repo to GitHub (Render connects to GitHub; Origin mirror may need linking)
2. [render.com](https://render.com) → **New → Blueprint** → select repo
   - Uses [`render.yaml`](../render.yaml) — service name **`nous-auth`**
3. Before deploy, set secret env vars in Render dashboard:

```bash
./scripts/render_env_export.sh
```

4. Set `BETTER_AUTH_URL=https://nous-auth.onrender.com` (must match service URL)
5. Deploy → wait for green health on `/health`

## 4. Local app (already wired if you ran setup)

```bash
./scripts/setup_path_a_auth.sh https://nous-auth.onrender.com
```

Restart Nous: `cd desktop && npm run tauri dev`

## 5. Verify

```bash
./scripts/verify_hosted_auth.sh
```

Settings → Account → email → OTP from Resend inbox.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 404 on health | Service not deployed or wrong URL |
| OTP not received | Resend domain / `RESEND_FROM` / spam folder |
| Session invalid | `BETTER_AUTH_URL` mismatch on Render |
| Cloud Watch auth fail | Root `.env` `AUTH_URL` must be Render HTTPS, restart Docker |
