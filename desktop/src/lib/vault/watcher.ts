/** Future-proof hook for auto-ingest on vault changes. Phase 2: wire Tauri watch + debounced api.ingest. */
export type VaultChangeHandler = (path: string) => void;

export function startVaultWatcher(_onChange: VaultChangeHandler): () => void {
  // Stub — no-op until file watching is implemented
  return () => {};
}