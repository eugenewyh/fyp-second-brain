import { describe, expect, it } from "vitest";
import { filterVaultTree } from "./load";
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

describe("filterVaultTree", () => {
  it("returns full tree when query is empty", () => {
    expect(filterVaultTree(sampleTree, "")).toEqual(sampleTree);
  });

  it("filters to matching file names including nested entries", () => {
    const filtered = filterVaultTree(sampleTree, "java");
    const serialized = JSON.stringify(filtered);
    expect(serialized).toContain("java.pdf");
  });

  it("keeps parent folder when child matches", () => {
    const filtered = filterVaultTree(sampleTree, "lectures");
    expect(filtered[0].name).toBe("data/documents/");
  });
});