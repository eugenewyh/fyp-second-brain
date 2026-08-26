import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";
import {
  shouldUseSemanticSearch,
  fuzzySearchHits,
  semanticSearchHits,
  resolveSemanticSourcePath,
} from "./search-dispatch";
import type { VaultNode } from "./types";

const mdVaultFiles = [
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
  });

  it("resolves report bibliography labels (Personal — filename.md)", () => {
    expect(
      resolveSemanticSourcePath(
        "Personal — servlets.md",
        mdVaultFiles,
      ),
    ).toBe("/home/user/data/documents/research/servlets.md");
  });

  it("strips page suffixes from bibliography labels", () => {
    expect(
      resolveSemanticSourcePath("Personal — servlets.md, p.12", mdVaultFiles),
    ).toBe("/home/user/data/documents/research/servlets.md");
  });

  it("returns null for unresolvable bare PDF (real API shape)", () => {
    expect(resolveSemanticSourcePath("Lec03.pdf", mdVaultFiles)).toBeNull();
  });

  it("drops unresolvable hits from semanticSearchHits", () => {
    const hits = semanticSearchHits(
      [{ source: "Lec03.pdf", excerpt: "lecture chunk", distance: 0.2, page: 3 }],
      mdVaultFiles,
    );
    expect(hits).toHaveLength(0);
  });

  it("drops PDF even when present in vault index (non-md not editable)", () => {
    const vaultWithPdf = [
      ...mdVaultFiles,
      { path: "/home/user/data/documents/Lec03.pdf", name: "Lec03.pdf" },
    ];
    const hits = semanticSearchHits(
      [{ source: "Lec03.pdf", excerpt: "lecture", distance: 0.1, page: 1 }],
      vaultWithPdf,
    );
    expect(hits).toHaveLength(0);
  });

  it("keeps resolvable md hits from captured vault-search fixture", () => {
    const fixturePath = resolve(
      dirname(fileURLToPath(import.meta.url)),
      "../../../fixtures/vault-search-api.json",
    );
    const fixture = JSON.parse(readFileSync(fixturePath, "utf8")) as {
      results: { source: string; excerpt: string; distance: number; page: number | null }[];
    };
    const hits = semanticSearchHits(fixture.results, mdVaultFiles);
    expect(hits.every((h) => h.path.includes("/"))).toBe(true);
    expect(hits.some((h) => h.name === "Lec03.pdf")).toBe(false);
  });
});