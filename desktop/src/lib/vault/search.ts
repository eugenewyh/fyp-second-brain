import Fuse from "fuse.js";
import type { VaultNode, VaultSearchHit } from "./types";

function flattenNodes(nodes: VaultNode[]): VaultNode[] {
  const out: VaultNode[] = [];
  for (const node of nodes) {
    if (node.type === "file") out.push(node);
    if (node.children) out.push(...flattenNodes(node.children));
  }
  return out;
}

export function fuzzySearchVault(nodes: VaultNode[], query: string): VaultSearchHit[] {
  if (!query.trim()) return [];
  const files = flattenNodes(nodes);
  const fuse = new Fuse(files, { keys: ["name", "path"], threshold: 0.4 });
  return fuse.search(query).map((r) => ({
    path: r.item.path,
    name: r.item.name,
    score: r.score ?? 0,
  }));
}