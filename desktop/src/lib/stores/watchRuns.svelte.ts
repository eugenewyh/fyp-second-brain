import { api, type ResearchResult } from "$lib/api";
import { workspace } from "$lib/stores/workspace.svelte";

export type WatchRunPhase = "running" | "done" | "error" | "cancelled";

export interface WatchRunEntry {
  projectPath: string;
  watchId: string;
  name: string;
  status: string;
  phase: WatchRunPhase;
  abort: AbortController;
}

export function watchRunKey(projectPath: string, watchId: string): string {
  return `${projectPath}:${watchId || "legacy"}`;
}

class WatchRunsStore {
  entries = $state<Record<string, WatchRunEntry>>({});

  get active(): WatchRunEntry[] {
    return Object.values(this.entries).filter((e) => e.phase === "running");
  }

  get hasActive(): boolean {
    return this.active.length > 0;
  }

  get(projectPath: string, watchId: string): WatchRunEntry | undefined {
    return this.entries[watchRunKey(projectPath, watchId)];
  }

  isRunning(projectPath: string, watchId: string): boolean {
    return this.get(projectPath, watchId)?.phase === "running";
  }

  stop(projectPath: string, watchId: string): void {
    this.get(projectPath, watchId)?.abort.abort();
  }

  private patch(key: string, patch: Partial<WatchRunEntry> | null) {
    if (!patch) {
      const next = { ...this.entries };
      delete next[key];
      this.entries = next;
      return;
    }
    const cur = this.entries[key];
    if (!cur) return;
    this.entries = { ...this.entries, [key]: { ...cur, ...patch } };
  }

  private finish(key: string, phase: WatchRunPhase, status: string, refreshVault: boolean) {
    this.patch(key, { phase, status });
    if (refreshVault) workspace.requestVaultRefresh();
    window.setTimeout(() => {
      if (this.entries[key]?.phase === phase) this.patch(key, null);
    }, 4000);
  }

  async run(opts: {
    projectPath: string;
    watchId: string;
    name: string;
    sessionId?: string | null;
  }): Promise<ResearchResult | null> {
    const key = watchRunKey(opts.projectPath, opts.watchId);
    if (this.entries[key]?.phase === "running") return null;

    const abort = new AbortController();
    this.entries = {
      ...this.entries,
      [key]: {
        projectPath: opts.projectPath,
        watchId: opts.watchId,
        name: opts.name,
        status: "Starting scheduled research…",
        phase: "running",
        abort,
      },
    };

    try {
      const result = await api.watchStream(
        opts.projectPath,
        (ev) => {
          const d = "detail" in ev && typeof ev.detail === "string" ? ev.detail : "";
          if (d) this.patch(key, { status: d });
          if (ev.type === "watch_brief") {
            this.patch(key, {
              status: ev.slow_day ? "Slow day — nothing new to rehash." : "Writing brief…",
            });
          }
          if (ev.type === "result") {
            this.patch(key, {
              status: ev.result.slow_day ? "Slow day — nothing new to rehash." : "Writing brief…",
            });
          }
        },
        abort.signal,
        { sessionId: opts.sessionId ?? null, watchId: opts.watchId, force: true },
      );
      const doneMsg = result.slow_day
        ? "Slow day — nothing new to rehash."
        : "Brief written.";
      this.finish(key, "done", doneMsg, true);
      return result;
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") {
        this.finish(key, "cancelled", "Cancelled", false);
      } else {
        const msg = e instanceof Error ? e.message : "Scheduled research failed";
        this.finish(key, "error", msg, false);
      }
      return null;
    }
  }
}

export const watchRuns = new WatchRunsStore();
