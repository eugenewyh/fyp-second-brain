/** Paths Watch/Teach write that the vault watcher must not re-ingest. */
export function shouldSkipWatcherIngest(path: string): boolean {
  const p = path.replace(/\\/g, "/").toLowerCase();
  if (p.endsWith("/instruction.md")) return true;
  return ["/briefs/", "/memory/", "/research/", "/watches/"].some((seg) => p.includes(seg));
}
