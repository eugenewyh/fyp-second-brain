import { describe, expect, it } from "vitest";
import type { VaultNode } from "./types";
import {
  buildVaultGraph,
  classifyPath,
  selectBodiesToRead,
  MAX_NODES,
} from "./vault-graph";
import { flattenVaultFiles } from "./flatten";

const tree: VaultNode[] = [
  {
    name: "Inbox",
    path: "/vault/Inbox",
    type: "folder",
    children: [
      { name: "alpha.md", path: "/vault/Inbox/alpha.md", type: "file" },
      { name: "beta.md", path: "/vault/Inbox/beta.md", type: "file" },
    ],
  },
  {
    name: "research",
    path: "/vault/research",
    type: "folder",
    children: [
      { name: "2026-08-01-report.md", path: "/vault/research/2026-08-01-report.md", type: "file" },
    ],
  },
  {
    name: "memory",
    path: "/vault/memory",
    type: "folder",
    children: [
      {
        name: "learnings",
        path: "/vault/memory/learnings",
        type: "folder",
        children: [
          { name: "card.md", path: "/vault/memory/learnings/card.md", type: "file" },
        ],
      },
      {
        name: "agents",
        path: "/vault/memory/agents",
        type: "folder",
        children: [
          {
            name: "sess-1",
            path: "/vault/memory/agents/sess-1",
            type: "folder",
            children: [
              {
                name: "learnings",
                path: "/vault/memory/agents/sess-1/learnings",
                type: "folder",
                children: [
                  {
                    name: "agent-card.md",
                    path: "/vault/memory/agents/sess-1/learnings/agent-card.md",
                    type: "file",
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        name: "digests",
        path: "/vault/memory/digests",
        type: "folder",
        children: [
          { name: "2026-08-04.md", path: "/vault/memory/digests/2026-08-04.md", type: "file" },
        ],
      },
    ],
  },
];

const bodies: Record<string, string> = {
  "/vault/Inbox/alpha.md": "# Alpha\n\nSee [[beta]] for more.\n",
  "/vault/Inbox/beta.md": "# Beta\n",
  "/vault/research/2026-08-01-report.md": "# Report\n",
  "/vault/memory/learnings/card.md":
    '---\ntype: learning\nreport_path: "/vault/research/2026-08-01-report.md"\n---\n\n# Learning\n',
  "/vault/memory/agents/sess-1/learnings/agent-card.md":
    '---\ntype: learning\nreport_path: "/vault/research/2026-08-01-report.md"\n---\n\n# Agent Learning\n',
  "/vault/memory/digests/2026-08-04.md": "# Digest\n",
};

describe("classifyPath", () => {
  it("classifies by folder", () => {
    expect(classifyPath("/vault/Inbox/a.md")).toBe("note");
    expect(classifyPath("/vault/research/r.md")).toBe("research");
    expect(classifyPath("/vault/memory/learnings/c.md")).toBe("learning");
    expect(classifyPath("/vault/memory/agents/sess-1/learnings/c.md")).toBe("learning");
    expect(classifyPath("/vault/memory/digests/d.md")).toBe("digest");
    expect(classifyPath("/vault/Inbox/briefs/2026-08-17.md")).toBe("digest");
  });
});

describe("buildVaultGraph", () => {
  it("builds typed nodes and wikilink/topic/provenance edges", () => {
    const g = buildVaultGraph(tree, bodies);
    const types = new Map(g.nodes.map((n) => [n.id, n.type]));
    expect(types.get("/vault/Inbox/alpha.md")).toBe("note");
    expect(types.get("/vault/research/2026-08-01-report.md")).toBe("research");
    expect(types.get("/vault/memory/learnings/card.md")).toBe("learning");
    expect(types.get("/vault/memory/agents/sess-1/learnings/agent-card.md")).toBe("learning");
    expect(types.get("/vault/memory/digests/2026-08-04.md")).toBe("digest");
    expect(types.get("/vault/Inbox")).toBe("topic");
    // research/memory are not topics
    expect(types.has("/vault/research")).toBe(false);

    const kinds = g.links.map((l) => `${l.kind}:${l.source}->${l.target}`);
    expect(kinds).toContain("wikilink:/vault/Inbox/alpha.md->/vault/Inbox/beta.md");
    expect(kinds).toContain("topic:/vault/Inbox->/vault/Inbox/alpha.md");
    expect(kinds).toContain(
      "provenance:/vault/memory/learnings/card.md->/vault/research/2026-08-01-report.md",
    );
    expect(kinds).toContain(
      "provenance:/vault/memory/agents/sess-1/learnings/agent-card.md->/vault/research/2026-08-01-report.md",
    );
  });

  it("filters node types", () => {
    const g = buildVaultGraph(tree, bodies, { types: { learning: false, digest: false } });
    expect(g.nodes.some((n) => n.type === "learning")).toBe(false);
    expect(g.nodes.some((n) => n.type === "digest")).toBe(false);
  });

  it("focuses a neighborhood", () => {
    const g = buildVaultGraph(tree, bodies, { focusId: "/vault/Inbox/alpha.md" });
    expect(g.nodes.some((n) => n.id === "/vault/Inbox/alpha.md")).toBe(true);
    expect(g.nodes.some((n) => n.id === "/vault/Inbox/beta.md")).toBe(true);
    expect(g.nodes.some((n) => n.type === "digest")).toBe(false);
  });

  it("computes degree", () => {
    const g = buildVaultGraph(tree, bodies);
    const alpha = g.nodes.find((n) => n.id === "/vault/Inbox/alpha.md");
    expect(alpha?.degree).toBeGreaterThan(0);
  });

  it("caps by highest degree when over MAX_NODES", () => {
    const manyChildren: VaultNode[] = [];
    const manyBodies: Record<string, string> = {};
    // Hub note linked from many others → highest degree
    manyBodies["/vault/hub.md"] = "# Hub\n";
    manyChildren.push({ name: "hub.md", path: "/vault/hub.md", type: "file" });
    for (let i = 0; i < MAX_NODES + 20; i++) {
      const p = `/vault/n${i}.md`;
      manyChildren.push({ name: `n${i}.md`, path: p, type: "file" });
      manyBodies[p] = `# N${i}\n\nSee [[hub]].\n`;
    }
    const bigTree: VaultNode[] = [
      { name: "vault", path: "/vault", type: "folder", children: manyChildren },
    ];
    const g = buildVaultGraph(bigTree, manyBodies, { types: { topic: false } });
    expect(g.truncated).toBe(true);
    expect(g.nodes.length).toBeLessThanOrEqual(MAX_NODES);
    expect(g.nodes.some((n) => n.id === "/vault/hub.md")).toBe(true);
  });

  it("selectBodiesToRead prioritizes learnings over notes", () => {
    const files = flattenVaultFiles(tree).filter((f) => f.path.endsWith(".md"));
    const picked = selectBodiesToRead(files, 2);
    expect(picked.length).toBe(2);
    expect(picked[0].path).toContain("learnings");
  });

  it("treats topic briefs like digests and skips instruction.md", () => {
    const t: VaultNode[] = [
      {
        name: "Inbox",
        path: "/vault/Inbox",
        type: "folder",
        children: [
          { name: "instruction.md", path: "/vault/Inbox/instruction.md", type: "file" },
          {
            name: "briefs",
            path: "/vault/Inbox/briefs",
            type: "folder",
            children: [
              { name: "2026-08-17.md", path: "/vault/Inbox/briefs/2026-08-17.md", type: "file" },
            ],
          },
        ],
      },
    ];
    const g = buildVaultGraph(t, {
      "/vault/Inbox/instruction.md": "# Watch\n",
      "/vault/Inbox/briefs/2026-08-17.md": "# Morning Brief\n",
    });
    expect(g.nodes.some((n) => n.id.endsWith("instruction.md"))).toBe(false);
    expect(g.nodes.find((n) => n.id.endsWith("2026-08-17.md"))?.type).toBe("digest");
  });
});
