import { api, resetSidecarUrlCache, waitForSidecar, WATCHES_API_VERSION } from "$lib/api";
import { getVaultRoot } from "$lib/vault/load";

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
  /** Auto vault re-index in progress. */
  reindexBusy = $state(false);
  /** Last auto-reindex failure (cleared on success / manual retry). */
  reindexError = $state("");
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
  /** Last cloud brief pull timestamp (ms). */
  #lastCloudPull = 0;
  #cloudPullTimer: ReturnType<typeof setInterval> | null = null;

  /** Avoid retry loops for the same reindex fingerprint until forced. */
  #healKey = "";

  get watchesApiStale(): boolean {
    return this.connected && this.watchesApi < WATCHES_API_VERSION;
  }

  setBriefsToday(count: number) {
    this.briefsToday = Math.max(0, Math.floor(count));
  }

  /** Push active watches to cloud and pull pending briefs when signed in. */
  async syncCloudWatches(opts?: { syncAll?: boolean }) {
    if (!this.cloudWatchConfigured) {
      try {
        await api.cloudWatchDelegate(false);
      } catch {
        /* sidecar may be down */
      }
      this.#stopCloudPullTimer();
      return;
    }
    try {
      await api.cloudWatchDelegate(true);
      if (opts?.syncAll !== false) {
        await api.cloudWatchSyncAll();
      }
      await this.#pullCloudBriefs();
      this.#ensureCloudPullTimer();
    } catch {
      /* background refresh — caller may surface errors */
    }
  }

  async #pullCloudBriefs() {
    const pulled = await api.cloudWatchPull();
    this.#lastCloudPull = Date.now();
    if (pulled.count > 0) {
      const listed = await api.listWatches();
      this.briefsToday = listed.watches.filter((w) => w.has_brief_today).length;
    }
    return pulled;
  }

  #ensureCloudPullTimer() {
    if (this.#cloudPullTimer || !this.cloudWatchConfigured) return;
    this.#cloudPullTimer = setInterval(() => {
      if (!this.cloudWatchConfigured || !this.connected) return;
      void this.#pullCloudBriefs().catch(() => {});
    }, 15 * 60 * 1000);
  }

  #stopCloudPullTimer() {
    if (this.#cloudPullTimer) {
      clearInterval(this.#cloudPullTimer);
      this.#cloudPullTimer = null;
    }
  }

  /** True when signed in and cloud handles weekday morning briefs. */
  get cloudWatchesDelegated(): boolean {
    return this.cloudWatchAvailable && this.cloudWatchConfigured && this.cloudWatchHasKey;
  }

  /** True when Ask/Agent vault search should be blocked. */
  get memorySearchBlocked() {
    return this.connected && (!this.embeddingsOk || this.reindexRequired || this.reindexBusy);
  }

  async refreshStatus(opts?: { skipHeal?: boolean }) {
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
              /* Models key missing or sync failed */
            }
          }
          await this.syncCloudWatches();
        } else {
          await this.syncCloudWatches({ syncAll: false });
        }
      } catch {
        this.cloudWatchAvailable = false;
        this.cloudWatchConfigured = false;
        this.cloudWatchEmail = "";
        this.cloudWatchHasKey = false;
      }
      if (!opts?.skipHeal) void this.maybeAutoReindex();
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
      this.#stopCloudPullTimer();
    }
  }

  /** Rebuild the vault search index when the sidecar says re-ingest is required. */
  async maybeAutoReindex(opts?: { force?: boolean }): Promise<boolean> {
    if (!this.connected || this.reindexBusy) return false;
    if (!this.reindexRequired && !opts?.force) return false;
    const key = `${this.embeddingsProvider}:${this.embeddingsModel}:reindex`;
    if (!opts?.force && this.#healKey === key) return false;
    this.#healKey = key;
    this.reindexBusy = true;
    this.reindexError = "";
    try {
      const root = await getVaultRoot();
      await api.ingest(root, { reset: true });
      await this.refreshStatus({ skipHeal: true });
      if (this.reindexRequired || !this.embeddingsOk) {
        this.reindexError =
          this.embeddingsError || "Search index still needs attention after rebuild.";
        return false;
      }
      return true;
    } catch (e) {
      this.reindexError = e instanceof Error ? e.message : "Could not rebuild search index";
      return false;
    } finally {
      this.reindexBusy = false;
    }
  }

  /** Manual retry after auto-heal failed. */
  async retryReindex(): Promise<boolean> {
    this.#healKey = "";
    this.reindexError = "";
    return this.maybeAutoReindex({ force: true });
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
