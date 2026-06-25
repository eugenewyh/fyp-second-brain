import { describe, expect, it } from "vitest";
import {
  shouldUseSemanticSearch,
  fuzzySearchHits,
  semanticSearchHits,
} from "./search-dispatch";
import type { VaultNode } from "./types";

const sampleNodes: VaultNode[] = [
  {
    name: "research",
    path: "/vault/research",
    type: "folder",
    children: [
      { name: "servlets.md", path: "/vault/research/servlets.md", type: "file" },
    ],
  },
];

describe("search-dispatch", () => {
  it("selects semantic mode only when enabled", () => {
    expect(shouldUseSemanticSearch("semantic")).toBe(true);
    expect(shouldUseSemanticSearch("fuzzy")).toBe(false);
  });

  it("maps fuzzy hits from vault nodes", () => {
    const hits = fuzzySearchHits(sampleNodes, "servlet");
    expect(hits.length).toBeGreaterThan(0);
    expect(hits[0].name).toBe("servlets.md");
  });

  it("maps semantic API results to search hits with excerpts", () => {
    const hits = semanticSearchHits([
      {
        source: "/data/documents/servlets.md",
        excerpt: "Servlet lifecycle overview",
        distance: 0.12,
        page: null,
      },
    ]);
    expect(hits[0].path).toContain("servlets.md");
    expect(hits[0].excerpt).toContain("Servlet");
  });
});