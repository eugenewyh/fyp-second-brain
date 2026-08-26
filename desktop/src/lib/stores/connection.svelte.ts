import { api, resetSidecarUrlCache, waitForSidecar, WATCHES_API_VERSION } from "$lib/api";

class ConnectionStore {
  connected = $state(false);
  connectionError = $state("");
  collectionCount = $state(0);
  connecting = $state(false);
  embeddingsOk = $state(true);
  reindexRequired = $state(false);
  embeddingsError = $state("");
  embeddingsProvider = $state("fastembed");
  embeddingsModel = $state("");
  /** From GET /health. Below WATCHES_API_VERSION means Watch routes are stale. */
  watchesApi = $state(0);
  /** Last Watch planner failure from GET /api/review/status. */
  watchPlanError = $state("");
  /** Watches with a brief dated today (from list / refresh). */
  briefsToday = $state(0);
  /** Cloud Watch hosted service is configured on this build. */
  cloudWatchAvailable = $state(false);
  /** User has a Cloud Watch session. */
  cloudWatchConfigured = $state(false);
  cloudWatchEmail = $state("");
  cloudWatchHasKey = $state(false);

  get watchesApiStale(): boolean {
    return this.connected && this.watchesApi < WATCHES_API_VERSION;
  }

  setBriefsToday(count: number) {
    this.briefsToday = Math.max(0, Math.floor(count));
  }

  /** True when Ask/Agent vault search should be blocked. */
  get memorySearchBlocked() {
    return this.connected && (!this.embeddingsOk || this.reindexRequired);
  }

  async refreshStatus() {
    try {
      const status = await api.status();
      this.collectionCount = status.collection_count;
      this.connected = true;
      this.connectionError = "";
      this.embeddingsOk = status.embeddings_ok !== false;
      this.reindexRequired = !!status.reindex_required;
      this.embeddingsError = status.embeddings_error || "";
      this.embeddingsProvider = status.embeddings_provider || "fastembed";
      this.embeddingsModel = status.embeddings_model || "";
      try {
        const health = await api.health();
        this.watchesApi = typeof health.watches_api === "number" ? health.watches_api : 0;
      } catch {
        this.watchesApi = 0;
      }
      try {
        const review = await api.reviewStatus();
        this.watchPlanError = (review.last_watch_error || "").trim();
      } catch {
        this.watchPlanError = "";
      }
      try {
        const listed = await api.listWatches();
        this.briefsToday = listed.watches.filter((w) => w.has_brief_today).length;
      } catch {
        /* keep prior briefsToday */
      }
      try {
        const cw = await api.cloudWatchStatus();
        this.cloudWatchAvailable = !!cw.available;
        this.cloudWatchConfigured = !!(cw.signed_in || cw.configured);
        this.cloudWatchEmail = cw.user?.email || "";
        this.cloudWatchHasKey = !!cw.user?.has_api_key;
        if (this.cloudWatchConfigured) {
          if (!this.cloudWatchHasKey) {
            try {
              await api.cloudWatchSyncLlm();
              const again = await api.cloudWatchStatus();
              this.cloudWatchHasKey = !!again.user?.has_api_key;
            } catch {
              /* Models key missing or sync failed — Connectors shows Sync */
            }
          }
          const pulled = await api.cloudWatchPull();
          if (pulled.count > 0) {
            const listed = await api.listWatches();
            this.briefsToday = listed.watches.filter((w) => w.has_brief_today).length;
          }
        }
      } catch {
        this.cloudWatchAvailable = false;
        this.cloudWatchConfigured = false;
        this.cloudWatchEmail = "";
        this.cloudWatchHasKey = false;
      }
    } catch (e) {
      this.connected = false;
      this.connectionError =
        e instanceof Error ? e.message : "Can't reach the AI service";
      this.watchesApi = 0;
      this.watchPlanError = "";
      this.briefsToday = 0;
      this.cloudWatchAvailable = false;
      this.cloudWatchConfigured = false;
      this.cloudWatchEmail = "";
      this.cloudWatchHasKey = false;
    }
  }

  /** Restart the sidecar and reconnect. Use when Watch routes 404 on a running process. */
  async reloadService(): Promise<boolean> {
    this.connectionError = "";
    try {
      await api.restartSidecar();
      resetSidecarUrlCache();
    } catch {
      /* browser / vite-only, or restart failed — still try health */
    }
    const ready = await waitForSidecar(24);
    if (!ready) {
      this.connected = false;
      this.watchesApi = 0;
      this.watchPlanError = "";
      this.briefsToday = 0;
      this.cloudWatchAvailable = false;
      this.cloudWatchConfigured = false;
      this.cloudWatchEmail = "";
      this.cloudWatchHasKey = false;
      this.connectionError =
        "Can't reach the AI sidecar on port 8765. From the project root run: ./scripts/start_sidecar.sh";
      return false;
    }
    await this.refreshStatus();
    return this.connected;
  }

  /**
   * Wait for sidecar health; if still down, try Tauri restart_sidecar once.
   */
  async connect(opts?: { restart?: boolean }): Promise<boolean> {
    this.connecting = true;
    this.connectionError = "";
    try {
      let ready = await waitForSidecar(opts?.restart === false ? 20 : 10);
      if (!ready) {
        try {
          await api.restartSidecar();
          resetSidecarUrlCache();
          ready = await waitForSidecar(24);
        } catch {
          /* not in Tauri, or restart failed */
        }
      }
      if (!ready) {
        this.connected = false;
        this.connectionError =
          "Can't reach the AI sidecar on port 8765. From the project root run: ./scripts/start_sidecar.sh";
        return false;
      }
      await this.refreshStatus();
      return this.connected;
    } finally {
      this.connecting = false;
    }
  }
}

export const connection = new ConnectionStore();
