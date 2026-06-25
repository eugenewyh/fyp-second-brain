import type { VaultSearchResult } from "$lib/api";
import type { VaultFileRef } from "./flatten";
import { backlinksForNote, type BacklinkIndex } from "./backlinks";

export interface SuggestionItem {
  path: string;
  label: string;
  kind: "backlink" | "embedding";
  excerpt?: string;
}

export function mergeSuggestions(
  notePath: string | null,
  index: BacklinkIndex,
  embeddingHits: VaultSearchResult[],
  vaultFiles: VaultFileRef[],
  max = 8,
): SuggestionItem[] {
  const seen = new Set<string>();
  const items: SuggestionItem[] = [];

  for (const path of backlinksForNote(notePath, index)) {
    if (seen.has(path)) continue;
    seen.add(path);
    items.push({
      path,
      label: path.split("/").pop() ?? path,
      kind: "backlink",
    });
  }

  const activeName = notePath?.split("/").pop() ?? "";
  for (const hit of embeddingHits) {
    const base = hit.source.split("/").pop() ?? hit.source;
    if (base === activeName) continue;
    const file = vaultFiles.find((f) => f.name === base || f.path.endsWith(`/${base}`));
    const path = file?.path ?? hit.source;
    if (seen.has(path)) continue;
    seen.add(path);
    items.push({
      path,
      label: base,
      kind: "embedding",
      excerpt: hit.excerpt,
    });
  }

  return items.slice(0, max);
}