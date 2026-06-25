import { describe, expect, it } from "vitest";
import { activateWikilinkTarget } from "./wikilink-click";

describe("wikilink-click (post vault refresh)", () => {
  it("fails with stale vault index before refresh", () => {
    const stale = [{ path: "/v/old.md", name: "old.md" }];
    expect(activateWikilinkTarget("new-note", stale)).toBeNull();
  });

  it("resolves after vault index includes new note", () => {
    const fresh = [
      { path: "/v/old.md", name: "old.md" },
      { path: "/v/research/new-note.md", name: "new-note.md" },
    ];
    expect(activateWikilinkTarget("new-note", fresh)).toBe("/v/research/new-note.md");
  });
});