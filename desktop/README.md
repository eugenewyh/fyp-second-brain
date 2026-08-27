# Nous

Personal knowledge and autonomous research — a local-first desktop app built with Tauri + SvelteKit.

**Nous** (mind / intellect) searches *your* documents and the web, runs multi-agent research, and writes findings back into your vault.

## Brand

- Product name: **Nous**
- Logo: `static/brand/nous-logo.png`
- Window title / bundle name: configured in `src-tauri/tauri.conf.json`

## Dev

**Usual (app + Account OTP):** from the **repo root**, with Docker Desktop running:

```bash
./scripts/dev_desktop.sh
```

That starts auth Postgres + the auth API, then `npm run tauri dev`. Tauri already starts the Python sidecar. OTP codes go to `.auth-dev.log` (or Resend if configured).

**UI only** (no Account sign-in):

```bash
cd desktop
npm install
npm run tauri dev
```

Optional Cloud Scheduled Research with the all-in-one script:

```bash
DEV_CLOUD_WATCH=1 ./scripts/dev_desktop.sh
```

On macOS, `tauri dev` launches from a synced `.app` bundle so the Dock icon matches `app-icon.png`. If the icon looks stale after an icon change, quit the app and run:

```bash
npm run icons:generate && npm run sync:macos-app
```

Then restart dev. You can also open `Nous.dev.app` directly after syncing.

## Stack

- Tauri 2 + SvelteKit (frontend)
- Python FastAPI sidecar (research agents, retrieval)
