import { describe, expect, it } from "vitest";
import {
  firstMarkdownHeading,
  formatConfidence,
  groupPeekConnections,
  humanizePeekLabel,
  parsePeekMeta,
  peekConnectionRows,
  peekKindLabel,
  stripLiftedPeekMeta,
  uniquePeekNeighbors,
  type PeekNeighbor,
} from "./graph-peek";
import type { VaultGraphNode } from "./vault-graph";

function node(
  id: string,
  type: VaultGraphNode["type"],
  label = id.split("/").pop() ?? id,
): VaultGraphNode {
  return { id, label, type };
}

function row(
  id: string,
  type: VaultGraphNode["type"],
  kind: PeekNeighbor["kind"],
): PeekNeighbor {
  return { node: node(id, type), kind };
}

describe("groupPeekConnections", () => {
  it("puts topic folders in the breadcrumb and files on topic edges in members", () => {
    const grouped = groupPeekConnections([
      row("/vault/dlm", "topic", "topic"),
      row("/vault/dlm/memory", "topic", "topic"),
      row("/vault/dlm/notes/a.md", "note", "topic"),
      row("/vault/dlm/notes/b.md", "note", "wikilink"),
      row("/vault/research/r.md", "research", "provenance"),
      row("/vault/dlm/notes/c.md", "note", "semantic"),
    ]);
    expect(grouped.topics.map((r) => r.node.label)).toEqual(["dlm", "memory"]);
    expect(grouped.members.map((r) => r.node.id)).toEqual(["/vault/dlm/notes/a.md"]);
    expect(grouped.linked.map((r) => r.node.id)).toEqual(["/vault/dlm/notes/b.md"]);
    expect(grouped.related.map((r) => r.node.id)).toEqual(["/vault/dlm/notes/c.md"]);
    expect(grouped.provenance.map((r) => r.node.id)).toEqual(["/vault/research/r.md"]);
  });

  it("dedupes by node id, keeping the first occurrence", () => {
    const grouped = groupPeekConnections([
      row("/vault/n.md", "note", "wikilink"),
      row("/vault/n.md", "note", "semantic"),
    ]);
    expect(grouped.linked).toHaveLength(1);
    expect(grouped.related).toHaveLength(0);
  });

  it("lists linked, related, then provenance in the footer — not topic crumbs or members", () => {
    const grouped = groupPeekConnections([
      row("/vault/t", "topic", "topic"),
      row("/vault/in.md", "note", "topic"),
      row("/vault/a.md", "note", "wikilink"),
      row("/vault/b.md", "note", "semantic"),
      row("/vault/r.md", "research", "provenance"),
    ]);
    expect(peekConnectionRows(grouped).map((r) => r.node.id)).toEqual([
      "/vault/a.md",
      "/vault/b.md",
      "/vault/r.md",
    ]);
  });
});

describe("uniquePeekNeighbors", () => {
  it("keeps outgoing-first order", () => {
    const rows = uniquePeekNeighbors([
      row("/vault/a.md", "note", "wikilink"),
      row("/vault/b.md", "note", "wikilink"),
      row("/vault/a.md", "note", "semantic"),
    ]);
    expect(rows.map((r) => r.node.id)).toEqual(["/vault/a.md", "/vault/b.md"]);
  });
});

describe("peekKindLabel", () => {
  it("labels edge kinds for the connection list", () => {
    expect(peekKindLabel("wikilink")).toBe("Linked");
    expect(peekKindLabel("semantic")).toBe("Related");
    expect(peekKindLabel("provenance")).toBe("From report");
    expect(peekKindLabel("topic")).toBe("In topic");
  });
});

describe("parsePeekMeta", () => {
  it("uses the first heading as the title", () => {
    const meta = parsePeekMeta(
      "# Claim: Constrained decoding\n\nBody.\n",
      "the-paper-constrained-decoding",
    );
    expect(meta.title).toBe("Claim: Constrained decoding");
  });

  it("falls back to a humanized label when the heading is generic", () => {
    const meta = parsePeekMeta("# What we know\n\nA claim.\n", "the-paper-slug");
    expect(meta.title).toBe("The paper slug");
  });

  it("reads confidence from frontmatter", () => {
    const meta = parsePeekMeta(
      '---\nconfidence: 0.55\n---\n\n# Title\n',
      "slug",
    );
    expect(meta.confidence).toBeCloseTo(0.55);
    expect(meta.liftedConfidenceFromBody).toBe(false);
  });

  it("reads a Confidence line from the body", () => {
    const meta = parsePeekMeta(
      "# Title\n\nSome text.\n\n*Confidence: 55%*\n",
      "slug",
    );
    expect(meta.confidence).toBeCloseTo(0.55);
    expect(meta.liftedConfidenceFromBody).toBe(true);
  });

  it("lifts a standalone source URL", () => {
    const meta = parsePeekMeta(
      "# Title\n\nhttps://arxiv.org/abs/2607.07026\n",
      "slug",
    );
    expect(meta.sourceUrl).toBe("https://arxiv.org/abs/2607.07026");
    expect(meta.liftedUrlFromBody).toBe(true);
  });

  it("keeps inline URLs in the body", () => {
    const meta = parsePeekMeta(
      "# Title\n\nSee https://arxiv.org/abs/2607.07026 for the paper.\n",
      "slug",
    );
    expect(meta.sourceUrl).toBe("https://arxiv.org/abs/2607.07026");
    expect(meta.liftedUrlFromBody).toBe(false);
  });
});

describe("stripLiftedPeekMeta", () => {
  it("removes the confidence line and standalone URL that were lifted", () => {
    const raw = [
      "# Claim: The paper",
      "",
      "Cited as arXiv:2607.07026.",
      "",
      "https://arxiv.org/abs/2607.07026",
      "",
      "*Confidence: 55%*",
    ].join("\n");
    const meta = parsePeekMeta(raw, "slug");
    const stripped = stripLiftedPeekMeta(raw, meta);
    expect(stripped).toContain("Claim: The paper");
    expect(stripped).not.toMatch(/Confidence/i);
    expect(stripped).not.toContain("https://arxiv.org/abs/2607.07026");
  });
});

describe("humanizePeekLabel", () => {
  it("turns slugs into a readable fallback title", () => {
    expect(humanizePeekLabel("the-paper-constrained-decoding")).toBe(
      "The paper constrained decoding",
    );
  });
});

describe("firstMarkdownHeading", () => {
  it("returns the first atx heading", () => {
    expect(firstMarkdownHeading("para\n\n## Findings\n")).toBe("Findings");
  });
});

describe("formatConfidence", () => {
  it("renders a percent", () => {
    expect(formatConfidence(0.55)).toBe("55%");
  });
});
