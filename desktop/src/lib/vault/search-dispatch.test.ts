import { describe, expect, it } from "vitest";
import {
  shouldUseSemanticSearch,
  fuzzySearchHits,
  semanticSearchHits,
  resolveSemanticSourcePath,
} from "./search-dispatch";
import type { VaultNode } from "./types";

const vaultFiles = [
  { path: "/home/user/data/documents/research/servlets.md", name: "servlets.md" },
  { path: "/home/user/data/documents/java-overview.md", name: "java-overview.md" },
];

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

  it("maps fuzzy hits with full vault paths", () => {
    const hits = fuzzySearchHits(sampleNodes, "servlet");
    expect(hits[0].path).toBe("/vault/research/servlets.md");
    expect(hits[0].name).toBe("servlets.md");
  });

  it("resolves bare API filename to full vault path", () => {
    expect(resolveSemanticSourcePath("servlets.md", vaultFiles)).toBe(
      "/home/user/data/documents/research/servlets.md",
    );
  });

  it("resolves ingest-style path to vault file by basename", () => {
    expect(
      resolveSemanticSourcePath(
        "/Users/eugene/fyp-second-brain/data/chroma/sources/servlets.md",
        vaultFiles,
      ),
    ).toBe("/home/user/data/documents/research/servlets.md");
  });

  it("maps semantic API results to openable full paths", () => {
    const hits = semanticSearchHits(
      [
        {
          source: "servlets.md",
          excerpt: "Servlet lifecycle overview",
          distance: 0.12,
          page: null,
        },
      ],
      vaultFiles,
    );
    expect(hits[0].path).toBe("/home/user/data/documents/research/servlets.md");
    expect(hits[0].excerpt).toContain("Servlet");
  });
});