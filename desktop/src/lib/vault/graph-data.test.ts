import { describe, expect, it } from "vitest";
import { buildGraphData } from "./graph-data";
import { buildBacklinkIndex } from "./backlinks";

const files = [
  { path: "/vault/A.md", name: "A.md" },
  { path: "/vault/B.md", name: "B.md" },
];

describe("graph-data", () => {
  it("builds nodes and links for active note", () => {
    const bodies = {
      "/vault/A.md": "Link to [[B]]",
      "/vault/B.md": "Back to [[A]]",
    };
    const index = buildBacklinkIndex(files, bodies);
    const data = buildGraphData("/vault/A.md", index, bodies, files, ["/vault/B.md"]);
    expect(data.nodes.length).toBeGreaterThanOrEqual(2);
    expect(data.links.some((l) => l.kind === "wikilink")).toBe(true);
  });
});