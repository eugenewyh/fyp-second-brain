import type { VaultSearchHit } from "./types";
import { fuzzySearchVault } from "./search";
import type { VaultNode } from "./types";
import type { VaultSearchResult } from "$lib/api";
import type { VaultFileRef } from "./flatten";
import { normalizeNoteName } from "./wikilinks";
import { sourceLookupName } from "./source-origin";

export type VaultSearchMode = "fuzzy" | "semantic";

export function shouldUseSemanticSearch(mode: VaultSearchMode): boolean {
  return mode === "semantic";
}

export function fuzzySearchHits(nodes: VaultNode[], query: string): VaultSearchHit[] {
  return fuzzySearchVault(nodes, query);
}

/** Map API source to a vault path openable in the UI; null when not in the vault index. */
export function resolveSemanticSourcePath(
  source: string,
  vaultFiles: VaultFileRef[],
): string | null {
  const lookup = sourceLookupName(source);
  const exact = vaultFiles.find((f) => f.path === source || f.path === lookup);
  if (exact) return exact.path;

  const basename = lookup.split(/[\\/]/).pop() ?? lookup;
  const byName = vaultFiles.find((f) => f.name === basename);
  if (byName) return byName.path;

  const want = normalizeNoteName(basename);
  const byStem = vaultFiles.find((f) => normalizeNoteName(f.name) === want);
  if (byStem) return byStem.path;

  const partial = vaultFiles.find((f) => normalizeNoteName(f.name).includes(want));
  return partial?.path ?? null;
}

function isEditableNotePath(path: string): boolean {
  return path.toLowerCase().endsWith(".md");
}

/** Only returns hits resolvable to an editable .md note (drops PDFs and other types). */
export function semanticSearchHits(
  results: VaultSearchResult[],
  vaultFiles: VaultFileRef[],
): VaultSearchHit[] {
  const hits: VaultSearchHit[] = [];
  for (const r of results) {
    const path = resolveSemanticSourcePath(r.source, vaultFiles);
    if (!path || !isEditableNotePath(path)) continue;
    hits.push({
      path,
      name: path.split("/").pop() ?? r.source,
      score: r.distance ?? 0,
      excerpt: r.excerpt,
    });
  }
  return hits;
}