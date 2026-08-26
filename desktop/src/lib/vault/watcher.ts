import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { api } from "$lib/api";
import { workspace } from "$lib/stores/workspace.svelte";
import { getVaultRoot } from "$lib/vault/load";
import { createDebouncedHandler } from "$lib/vault/watcher-debounce";
import { loadAutoIngestEnabled } from "$lib/vault/watcher-prefs";
import { shouldSkipWatcherIngest } from "$lib/vault/watcher-skip";

export type VaultChangeHandler = (path: string, kind?: string) => void;

const SUPPORTED = /\.(md|txt|pdf)$/i;

type VaultEventPayload = {
  path: string;
  kind?: string;
};

/**
 * Watch the vault for file + folder create/modify/remove.
 * Always refreshes UI; optionally auto-ingests supported files on create/modify.
 */
export async function startVaultWatcher(onChange: VaultChangeHandler): Promise<() => void> {
  const root = await getVaultRoot();
  await invoke("start_vault_watch", { root });

  // UI refresh: short debounce, coalesces Finder bulk ops
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;
  function scheduleUiRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => {
      refreshTimer = null;
      workspace.requestVaultRefresh();
      void workspace.syncProjectsFromDisk();
    }, 250);
  }

  // Ingest: longer debounce per file (existing behavior)
  const { schedule: scheduleIngest, cancelAll: cancelIngest } = createDebouncedHandler(
    async (path) => {
      if (!loadAutoIngestEnabled()) return;
      try {
        workspace.watcherStatus = "ingesting";
        await api.ingestFile(path);
        workspace.requestVaultRefresh();
        onChange(path, "ingest");
        workspace.watcherStatus = "idle";
      } catch (e) {
        workspace.watcherStatus = e instanceof Error ? e.message : "Ingest failed";
      }
    },
    2000,
  );

  const unlisten = await listen<VaultEventPayload>("vault-file-changed", (event) => {
    const path = event.payload?.path ?? "";
    const kind = event.payload?.kind ?? "other";
    if (!path) return;

    scheduleUiRefresh();
    onChange(path, kind);

    // Auto-ingest only for supported files that still exist (not removes)
    if (kind !== "remove" && SUPPORTED.test(path) && !shouldSkipWatcherIngest(path)) {
      scheduleIngest(path);
    }
  });

  return () => {
    if (refreshTimer) clearTimeout(refreshTimer);
    cancelIngest();
    void unlisten();
    void invoke("stop_vault_watch");
  };
}
