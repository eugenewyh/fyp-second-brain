import { describe, expect, it } from "vitest";
import { backlinksForNote, buildBacklinkIndex } from "./backlinks";

const files = [
  { path: "/vault/Target.md", name: "Target.md" },
  { path: "/vault/Referrer.md", name: "Referrer.md" },
];

describe("backlinks", () => {
  it("indexes notes that link to a target", () => {
    const index = buildBacklinkIndex(files, {
      "/vault/Referrer.md": "See [[Target]] for details.",
      "/vault/Target.md": "Standalone note.",
    });
    expect(backlinksForNote("/vault/Target.md", index)).toEqual(["/vault/Referrer.md"]);
  });

  it("returns empty when no backlinks", () => {
    const index = buildBacklinkIndex(files, {
      "/vault/Target.md": "No links here.",
    });
    expect(backlinksForNote("/vault/Target.md", index)).toEqual([]);
  });
});