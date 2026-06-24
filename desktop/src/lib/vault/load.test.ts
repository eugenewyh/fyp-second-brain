import { describe, expect, it } from "vitest";
import { filterVaultTree, isVaultTreeEmpty } from "./load";
import type { VaultNode } from "./types";

const sampleTree: VaultNode[] = [
  {
    name: "data/documents/",
    path: "/proj/data/documents",
    type: "folder",
    children: [
      { name: "notes.md", path: "/proj/data/documents/notes.md", type: "file" },
      {
        name: "lectures",
        path: "/proj/data/documents/lectures",
        type: "folder",
        children: [
          { name: "java.pdf", path: "/proj/data/documents/lectures/java.pdf", type: "file" },
        ],
      },
    ],
  },
];

describe("isVaultTreeEmpty", () => {
  it("returns true for empty array", () => {
    expect(isVaultTreeEmpty([])).toBe(true);
  });

  it("returns true for root folder with no children", () => {
    expect(
      isVaultTreeEmpty([
        { name: "data/documents/", path: "/proj/data/documents", type: "folder" },
      ]),
    ).toBe(true);
  });

  it("returns false when root has files", () => {
    expect(isVaultTreeEmpty(sampleTree)).toBe(false);
  });
});

describe("filterVaultTree", () => {
  it("returns full tree when query is empty", () => {
    expect(filterVaultTree(sampleTree, "")).toEqual(sampleTree);
  });

  it("filters to nested matching file via pruned parent folders", () => {
    const filtered = filterVaultTree(sampleTree, "java");
    expect(filtered).toHaveLength(1);
    expect(filtered[0].children).toHaveLength(1);
    expect(filtered[0].children?.[0].name).toBe("lectures");
    expect(filtered[0].children?.[0].children?.[0].name).toBe("java.pdf");
  });

  it("keeps parent folder when folder name matches", () => {
    const filtered = filterVaultTree(sampleTree, "lectures");
    expect(filtered[0].name).toBe("data/documents/");
    expect(filtered[0].children?.[0].name).toBe("lectures");
  });

  it("excludes non-matching siblings when a child matches", () => {
    const filtered = filterVaultTree(sampleTree, "java");
    const topChildren = filtered[0].children ?? [];
    expect(topChildren.some((c) => c.name === "notes.md")).toBe(false);
  });
});