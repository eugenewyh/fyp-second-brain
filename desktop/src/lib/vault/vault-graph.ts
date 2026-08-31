import type { VaultFileRef } from "./flatten";
import type { VaultNode } from "./types";
import { flattenVaultFiles } from "./flatten";
import { parseWikilinks, resolveWikilinkTarget } from "./wikilinks";
import { splitFrontmatter } from "./markdown";
import { topicsFromTree } from "./topics";

export type VaultNodeType = "note" | "research" | "learning" | "digest" | "topic";

export type VaultEdgeKind = "wikilink" | "topic" | "provenance" | "semantic";

export interface VaultGraphNode {
  id: string;
  label: string;
  type: VaultNodeType;
  /** 1 = normal; higher = more connected */
  degree?: number;
}

export interface VaultGraphLink {
  source: string;
  target: string;
  kind: VaultEdgeKind;
}

export interface VaultGraphData {
  nodes: VaultGraphNode[];
  links: VaultGraphLink[];
  /** True when node cap kicked in — graph is truncated */
  truncated: boolean;
  totalFiles: number;
}

export interface VaultGraphFilters {
  types?: Partial<Record<VaultNodeType, boolean>>;
  /** Filter to a single topic folder path (null = all) */
  topicPath?: string | null;
  /** Focus neighborhood of this node id (2 hops) */
  focusId?: string | null;
}

export const MAX_NODES = 300;
/** Cap how many note bodies are read when building the graph */
export const MAX_BODY_READS = 150;

const TYPE_LABEL: Record<VaultNodeType, string> = {
  note: "Note",
  research: "Research",
  learning: "Learning",
  digest: "Digest",
  topic: "Topic",
};

/** Prefer memory/research files, then notes, when budgeting body reads. */
const BODY_PRIORITY: Record<VaultNodeType, number> = {
  learning: 0,
  digest: 1,
  research: 2,
  note: 3,
  topic: 4,
};

export function vaultNodeTypeLabel(t: VaultNodeType): string {
  return TYPE_LABEL[t];
}

function stripExt(name: string): string {
  return name.replace(/\.(md|pdf|txt|docx)$/i, "");
}

export function classifyPath(path: string): VaultNodeType {
  const p = path.replace(/\\/g, "/");
  if (/\/briefs\//.test(p) || /\/memory\/digests\//.test(p)) return "digest";
  if (/\/memory\/(?:agents\/[^/]+\/)?learnings\//.test(p)) return "learning";
  if (/\/research\//.test(p)) return "research";
  return "note";
}

/**
 * Pick which markdown files to read for wikilink/provenance edges,
 * preferring learnings/digests/research over plain notes.
 */
export function selectBodiesToRead(
  files: VaultFileRef[],
  limit = MAX_BODY_READS,
): VaultFileRef[] {
  const md = files.filter((f) => f.path.endsWith(".md"));
  return [...md]
    .sort((a, b) => {
      const pa = BODY_PRIORITY[classifyPath(a.path)] ?? 9;
      const pb = BODY_PRIORITY[classifyPath(b.path)] ?? 9;
      if (pa !== pb) return pa - pb;
      return a.path.localeCompare(b.path);
    })
    .slice(0, Math.max(0, limit));
}

/** Frontmatter `report_path` (learning → report provenance). */
function frontmatterReportPath(content: string): string | null {
  const { frontmatter } = splitFrontmatter(content);
  const m = frontmatter.match(/^report_path:\s*"?([^"\n]+)"?\s*$/m);
  return m ? m[1].trim() : null;
}

function topFolderFor(path: string, topics: { path: string }[]): string | null {
  const norm = path.replace(/\\/g, "/");
  let best: string | null = null;
  for (const t of topics) {
    const tp = t.path.replace(/\\/g, "/");
    if (norm === tp || norm.startsWith(tp + "/")) {
      if (!best || tp.length > best.length) best = t.path;
    }
  }
  return best;
}

/**
 * Build the vault-wide knowledge graph from the loaded tree.
 * Nodes: notes, research reports, learning cards, digests, topic folders.
 * Edges: wikilinks, topic membership, learning→report provenance.
 * When over the node cap, keeps the highest-degree nodes (most connected).
 */
export function buildVaultGraph(
  nodes: VaultNode[],
  bodies: Record<string, string>,
  filters: VaultGraphFilters = {},
): VaultGraphData {
  const files = flattenVaultFiles(nodes).filter((f) => {
    if (!f.path.endsWith(".md")) return false;
    const p = f.path.replace(/\\/g, "/").toLowerCase();
    return !p.endsWith("/instruction.md");
  });
  const topics = topicsFromTree(nodes).filter(
    (t) => !["research", "memory"].includes(t.name.toLowerCase()),
  );

  // Resolve topic filter to a set of allowed file paths
  let allowedPaths: Set<string> | null = null;
  if (filters.topicPath) {
    allowedPaths = new Set(
      flattenVaultFiles(nodes)
        .filter((f) => f.path.startsWith(filters.topicPath + "/"))
        .map((f) => f.path),
    );
  }

  const typeOn = (t: VaultNodeType) => filters.types?.[t] !== false;

  // Candidate nodes (full set before degree-based cap)
  const candidates: VaultGraphNode[] = [];
  for (const f of files) {
    if (allowedPaths && !allowedPaths.has(f.path)) continue;
    const type = classifyPath(f.path);
    if (!typeOn(type)) continue;
    candidates.push({ id: f.path, label: stripExt(f.name), type });
  }
  for (const t of topics) {
    if (!typeOn("topic")) continue;
    if (filters.topicPath && t.path !== filters.topicPath) continue;
    candidates.push({ id: t.path, label: t.name, type: "topic" });
  }

  const candidateIds = new Set(candidates.map((n) => n.id));

  // Edges among all candidates first (so degree ranking is meaningful)
  const links: VaultGraphLink[] = [];
  const seen = new Set<string>();
  const push = (source: string, target: string, kind: VaultEdgeKind, idSet: Set<string>) => {
    if (!idSet.has(source) || !idSet.has(target) || source === target) return;
    const key = `${kind}:${source}->${target}`;
    if (seen.has(key)) return;
    seen.add(key);
    links.push({ source, target, kind });
  };

  for (const n of candidates) {
    if (n.type === "topic") continue;
    const topic = topFolderFor(n.id, topics);
    if (topic && candidateIds.has(topic)) push(topic, n.id, "topic", candidateIds);
  }

  const fileRefs: VaultFileRef[] = files;
  for (const f of files) {
    if (!candidateIds.has(f.path)) continue;
    const body = bodies[f.path];
    if (!body) continue;

    for (const link of parseWikilinks(body)) {
      const targetPath = resolveWikilinkTarget(link.target, fileRefs);
      if (targetPath && candidateIds.has(targetPath)) {
        push(f.path, targetPath, "wikilink", candidateIds);
      }
    }

    if (classifyPath(f.path) === "learning") {
      const rp = frontmatterReportPath(body);
      if (rp) {
        const match = files.find(
          (x) => x.path === rp || x.path.endsWith(rp) || rp.endsWith(x.name),
        );
        if (match && candidateIds.has(match.path)) {
          push(f.path, match.path, "provenance", candidateIds);
        }
      }
    }
  }

  // Degree for ranking + sizing
  const degree = new Map<string, number>();
  for (const l of links) {
    degree.set(l.source, (degree.get(l.source) ?? 0) + 1);
    degree.set(l.target, (degree.get(l.target) ?? 0) + 1);
  }
  for (const n of candidates) n.degree = degree.get(n.id) ?? 0;

  let truncated = false;
  let nodeList = candidates;
  if (nodeList.length > MAX_NODES) {
    truncated = true;
    // Keep highest-degree nodes; break ties by type priority then path
    nodeList = [...candidates]
      .sort((a, b) => {
        const da = a.degree ?? 0;
        const db = b.degree ?? 0;
        if (db !== da) return db - da;
        const pa = BODY_PRIORITY[a.type] ?? 9;
        const pb = BODY_PRIORITY[b.type] ?? 9;
        if (pa !== pb) return pa - pb;
        return a.id.localeCompare(b.id);
      })
      .slice(0, MAX_NODES);
  }

  const nodeIds = new Set(nodeList.map((n) => n.id));
  const cappedLinks = links.filter((l) => nodeIds.has(l.source) && nodeIds.has(l.target));
  links.length = 0;
  links.push(...cappedLinks);

  // Focus filter: keep neighborhood of focusId (2 hops)
  if (filters.focusId && nodeIds.has(filters.focusId)) {
    const keep = new Set<string>([filters.focusId]);
    for (let hop = 0; hop < 2; hop++) {
      for (const l of links) {
        if (keep.has(l.source)) keep.add(l.target);
        if (keep.has(l.target)) keep.add(l.source);
      }
    }
    nodeList = nodeList.filter((n) => keep.has(n.id));
    const filtered = links.filter((l) => keep.has(l.source) && keep.has(l.target));
    links.length = 0;
    links.push(...filtered);
  }

  // Recompute degree on the final edge set
  const finalDegree = new Map<string, number>();
  for (const l of links) {
    finalDegree.set(l.source, (finalDegree.get(l.source) ?? 0) + 1);
    finalDegree.set(l.target, (finalDegree.get(l.target) ?? 0) + 1);
  }
  for (const n of nodeList) n.degree = finalDegree.get(n.id) ?? 0;

  return { nodes: nodeList, links, truncated, totalFiles: files.length };
}
