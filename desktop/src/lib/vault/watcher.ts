import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { api } from "$lib/api";
import { workspace } from "$lib/stores/workspace.svelte";
import { getVaultRoot } from "$lib/vault/load";
import { createDebouncedHandler } from "$lib/vault/watcher-debounce";
import { loadAutoIngestEnabled } from "$lib/vault/watcher-prefs";

export type VaultChangeHandler = (path: string) => void;

const SUPPORTED = /\.(md|txt|pdf)$/i;

export async function startVaultWatcher(onChange: VaultChangeHandler): Promise<() => void> {
  const root = await getVaultRoot();
  await invoke("start_vault_watch", { root });

  const { schedule, cancelAll } = createDebouncedHandler(async (path) => {
    if (!loadAutoIngestEnabled()) return;
    try {
      workspace.watcherStatus = "ingesting";
      await api.ingestFile(path);
      workspace.requestVaultRefresh();
      onChange(path);
      workspace.watcherStatus = "idle";
    } catch (e) {
      workspace.watcherStatus = e instanceof Error ? e.message : "Ingest failed";
    }
  });

  const unlisten = await listen<{ path: string }>("vault-file-changed", (event) => {
    const path = event.payload.path;
    if (SUPPORTED.test(path)) schedule(path);
  });

  return () => {
    cancelAll();
    void unlisten();
    void invoke("stop_vault_watch");
  };
}