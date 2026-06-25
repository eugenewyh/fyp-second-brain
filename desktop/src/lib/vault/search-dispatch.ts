import type { VaultSearchHit } from "./types";
import { fuzzySearchVault } from "./search";
import type { VaultNode } from "./types";
import type { VaultSearchResult } from "$lib/api";

export type VaultSearchMode = "fuzzy" | "semantic";

export function shouldUseSemanticSearch(mode: VaultSearchMode): boolean {
  return mode === "semantic";
}

export function fuzzySearchHits(nodes: VaultNode[], query: string): VaultSearchHit[] {
  return fuzzySearchVault(nodes, query);
}

export function semanticSearchHits(results: VaultSearchResult[]): VaultSearchHit[] {
  return results.map((r) => ({
    path: r.source,
    name: r.source.split("/").pop() ?? r.source,
    score: r.distance ?? 0,
    excerpt: r.excerpt,
  }));
}