const STORAGE_KEY = "second-brain-auto-ingest";

/** Always on — vault files are indexed for search without a Settings toggle. */
export function loadAutoIngestEnabled(): boolean {
  return true;
}

export function saveAutoIngestEnabled(enabled: boolean): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(STORAGE_KEY, String(enabled));
}
