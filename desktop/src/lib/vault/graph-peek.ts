import { splitFrontmatter } from "./markdown";
import type { VaultEdgeKind, VaultGraphNode, VaultNodeType } from "./vault-graph";

export interface PeekNeighbor {
  node: VaultGraphNode;
  kind: VaultEdgeKind;
}

export interface PeekConnections {
  /** Parent topic folders — header breadcrumb only. */
  topics: PeekNeighbor[];
  /** Wikilink neighbors. */
  linked: PeekNeighbor[];
  /** Semantic neighbors. */
  related: PeekNeighbor[];
  /** Learning → report provenance. */
  provenance: PeekNeighbor[];
  /** Files in a topic (when the selected node is a folder). */
  members: PeekNeighbor[];
}

export interface PeekMeta {
  title: string;
  /** 0–1 when known. */
  confidence: number | null;
  sourceUrl: string | null;
  liftedConfidenceFromBody: boolean;
  liftedUrlFromBody: boolean;
}

const GENERIC_HEADING = /^(what we know|claim)$/i;
const CONFIDENCE_LINE = /^\s*\*?Confidence:\s*(\d+(?:\.\d+)?)%?\*?\s*$/im;
const STANDALONE_URL = /^\s*(https?:\/\/[^\s)<>]+)\s*$/im;

export function uniquePeekNeighbors(rows: PeekNeighbor[]): PeekNeighbor[] {
  const seen = new Set<string>();
  const out: PeekNeighbor[] = [];
  for (const row of rows) {
    if (seen.has(row.node.id)) continue;
    seen.add(row.node.id);
    out.push(row);
  }
  return out;
}

/** Topic folders shortest-path-first (root → leaf). */
export function sortTopicBreadcrumb(topics: PeekNeighbor[]): PeekNeighbor[] {
  return [...topics].sort((a, b) => a.node.id.length - b.node.id.length);
}

/**
 * Split graph neighbors for the peek chrome.
 * Topic *folders* become breadcrumbs; topic *membership* of files becomes
 * the topic-node body list; the rest is the Connected footer.
 */
export function groupPeekConnections(rows: PeekNeighbor[]): PeekConnections {
  const unique = uniquePeekNeighbors(rows);
  const topics: PeekNeighbor[] = [];
  const linked: PeekNeighbor[] = [];
  const related: PeekNeighbor[] = [];
  const provenance: PeekNeighbor[] = [];
  const members: PeekNeighbor[] = [];

  for (const row of unique) {
    if (row.node.type === "topic") {
      topics.push(row);
      continue;
    }
    if (row.kind === "topic") {
      members.push(row);
      continue;
    }
    if (row.kind === "wikilink") linked.push(row);
    else if (row.kind === "semantic") related.push(row);
    else if (row.kind === "provenance") provenance.push(row);
    else members.push(row);
  }

  return {
    topics: sortTopicBreadcrumb(topics),
    linked,
    related,
    provenance,
    members,
  };
}

export function peekKindLabel(kind: VaultEdgeKind): string {
  if (kind === "semantic") return "Related";
  if (kind === "provenance") return "From report";
  if (kind === "topic") return "In topic";
  return "Linked";
}

export function peekConnectionRows(grouped: PeekConnections): PeekNeighbor[] {
  return [...grouped.linked, ...grouped.related, ...grouped.provenance];
}

export function humanizePeekLabel(label: string): string {
  const t = label
    .replace(/\.(md|txt|pdf|docx)$/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!t) return label;
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export function firstMarkdownHeading(body: string): string | null {
  for (const line of body.split(/\r?\n/)) {
    const m = line.match(/^#{1,3}\s+(.+?)\s*$/);
    if (m) return m[1].trim();
  }
  return null;
}

function parseFrontmatterFields(frontmatter: string): Record<string, string> {
  const fields: Record<string, string> = {};
  const inner = frontmatter.replace(/^---\r?\n/, "").replace(/\r?\n---\s*$/, "");
  for (const line of inner.split(/\r?\n/)) {
    const idx = line.indexOf(":");
    if (idx < 1) continue;
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    fields[key] = value;
  }
  return fields;
}

function parseConfidenceValue(raw: string): number | null {
  const n = Number.parseFloat(raw);
  if (!Number.isFinite(n)) return null;
  if (n > 1) return Math.min(1, n / 100);
  if (n < 0) return null;
  return n;
}

function firstUrl(text: string): string | null {
  const m = text.match(/https?:\/\/[^\s)<>]+/i);
  if (!m) return null;
  return m[0].replace(/[.,;:]+$/, "");
}

export function parsePeekMeta(raw: string | undefined, fallbackLabel: string): PeekMeta {
  const { frontmatter, body } = splitFrontmatter(raw ?? "");
  const fields = parseFrontmatterFields(frontmatter);

  let confidence: number | null = null;
  let liftedConfidenceFromBody = false;
  if (fields.confidence) confidence = parseConfidenceValue(fields.confidence);
  if (confidence == null) {
    const m = body.match(CONFIDENCE_LINE);
    if (m) {
      confidence = parseConfidenceValue(m[1]);
      liftedConfidenceFromBody = confidence != null;
    }
  } else if (CONFIDENCE_LINE.test(body)) {
    liftedConfidenceFromBody = true;
  }

  let sourceUrl: string | null = null;
  let liftedUrlFromBody = false;
  if (fields.source_path && /^https?:\/\//i.test(fields.source_path)) {
    sourceUrl = fields.source_path;
  } else {
    sourceUrl = firstUrl(body);
    if (sourceUrl) {
      const escaped = sourceUrl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      liftedUrlFromBody = new RegExp(`^\\s*${escaped}\\s*$`, "im").test(body);
    }
  }

  const heading = firstMarkdownHeading(body);
  const title =
    heading && !GENERIC_HEADING.test(heading)
      ? heading
      : humanizePeekLabel(fallbackLabel);

  return {
    title,
    confidence,
    sourceUrl,
    liftedConfidenceFromBody,
    liftedUrlFromBody,
  };
}

/** Drop body lines already shown in the peek meta bar. */
export function stripLiftedPeekMeta(body: string, meta: PeekMeta): string {
  const lines = body.split(/\r?\n/);
  const kept: string[] = [];
  let skippedUrl = !meta.liftedUrlFromBody;
  for (const line of lines) {
    if (meta.liftedConfidenceFromBody && CONFIDENCE_LINE.test(line)) {
      CONFIDENCE_LINE.lastIndex = 0;
      continue;
    }
    if (
      !skippedUrl &&
      meta.sourceUrl &&
      line.trim() === meta.sourceUrl
    ) {
      skippedUrl = true;
      continue;
    }
    kept.push(line);
  }
  return kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

export function confidenceTone(
  confidence: number | null,
): "default" | "success" | "warning" {
  if (confidence == null) return "default";
  if (confidence >= 0.7) return "success";
  if (confidence < 0.4) return "warning";
  return "default";
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function peekTypeLabel(type: VaultNodeType, path?: string): string {
  const p = (path ?? "").replace(/\\/g, "/");
  if (/\/memory\/claims\//i.test(p)) return "Claim";
  if (type === "note") return "Note";
  if (type === "research") return "Report";
  if (type === "learning") return "Learning";
  if (type === "digest") return "Digest";
  return "Topic";
}
