import type { VaultSearchHit } from "./types";
import { fuzzySearchVault } from "./search";
import type { VaultNode } from "./types";
import type { VaultSearchResult } from "$lib/api";
import type { VaultFileRef } from "./flatten";
import { normalizeNoteName } from "./wikilinks";

export type VaultSearchMode = "fuzzy" | "semantic";

export function shouldUseSemanticSearch(mode: VaultSearchMode): boolean {
  return mode === "semantic";
}

export function fuzzySearchHits(nodes: VaultNode[], query: string): VaultSearchHit[] {
  return fuzzySearchVault(nodes, query);
}

/** Map API source (often bare filename or ingest path) to full vault path for open/read. */
export function resolveSemanticSourcePath(source: string, vaultFiles: VaultFileRef[]): string {
  const exact = vaultFiles.find((f) => f.path === source);
  if (exact) return exact.path;

  const basename = source.split("/").pop() ?? source;
  const byName = vaultFiles.find((f) => f.name === basename);
  if (byName) return byName.path;

  const want = normalizeNoteName(basename);
  const byStem = vaultFiles.find((f) => normalizeNoteName(f.name) === want);
  if (byStem) return byStem.path;

  const partial = vaultFiles.find((f) => normalizeNoteName(f.name).includes(want));
  return partial?.path ?? source;
}

export function semanticSearchHits(
  results: VaultSearchResult[],
  vaultFiles: VaultFileRef[],
): VaultSearchHit[] {
  return results.map((r) => {
    const path = resolveSemanticSourcePath(r.source, vaultFiles);
    const name = path.split("/").pop() ?? r.source.split("/").pop() ?? r.source;
    return {
      path,
      name,
      score: r.distance ?? 0,
      excerpt: r.excerpt,
    };
  });
}