import type { VaultFileRef } from "./flatten";
import {
  backlinksForNote,
  outboundWikilinks,
  type BacklinkIndex,
} from "./backlinks";

export interface GraphNode {
  id: string;
  label: string;
  isActive?: boolean;
}

export interface GraphLink {
  source: string;
  target: string;
  kind: "wikilink" | "backlink" | "embedding";
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

const MAX_NODES = 30;

export function buildGraphData(
  activePath: string | null,
  index: BacklinkIndex,
  bodies: Record<string, string>,
  files: VaultFileRef[],
  embeddingNeighbors: string[] = [],
): GraphData {
  if (!activePath) return { nodes: [], links: [] };

  const nodeIds = new Set<string>([activePath]);
  const links: GraphLink[] = [];

  for (const target of outboundWikilinks(activePath, bodies, files)) {
    if (nodeIds.size < MAX_NODES) nodeIds.add(target);
    links.push({ source: activePath, target, kind: "wikilink" });
  }

  for (const source of backlinksForNote(activePath, index)) {
    if (nodeIds.size < MAX_NODES) nodeIds.add(source);
    links.push({ source, target: activePath, kind: "backlink" });
  }

  for (const neighbor of embeddingNeighbors) {
    if (nodeIds.size >= MAX_NODES) break;
    nodeIds.add(neighbor);
    links.push({ source: activePath, target: neighbor, kind: "embedding" });
  }

  const nodes: GraphNode[] = [...nodeIds].map((id) => ({
    id,
    label: id.split("/").pop() ?? id,
    isActive: id === activePath,
  }));

  return { nodes, links };
}