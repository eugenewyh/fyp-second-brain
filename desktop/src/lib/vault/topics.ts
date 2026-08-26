import type { VaultNode } from "./types";
import { flattenVaultFiles, type VaultFileRef } from "./flatten";

export interface KnowledgeTopic {
  id: string;
  name: string;
  path: string;
  /** First letter or monogram for rail icon */
  monogram: string;
}

/** Top-level folders become knowledge topics / project roots. */
export function topicsFromTree(nodes: VaultNode[]): KnowledgeTopic[] {
  return nodes
    .filter((n) => n.type === "folder")
    .map((n) => ({
      id: n.path,
      name: n.name,
      path: n.path,
      monogram: monogram(n.name),
    }));
}

export function monogram(name: string): string {
  const clean = name.replace(/[-_]+/g, " ").trim();
  if (!clean) return "?";
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return clean.slice(0, 2).toUpperCase();
}

export function findNodeByPath(nodes: VaultNode[], path: string): VaultNode | null {
  for (const n of nodes) {
    if (n.path === path) return n;
    if (n.children) {
      const hit = findNodeByPath(n.children, path);
      if (hit) return hit;
    }
  }
  return null;
}

/** Files under a topic folder (or all files if topicPath is null). */
export function filesForTopic(nodes: VaultNode[], topicPath: string | null): VaultFileRef[] {
  if (!topicPath) return flattenVaultFiles(nodes);
  const node = findNodeByPath(nodes, topicPath);
  if (!node) return [];
  if (node.type === "file") return [{ path: node.path, name: node.name }];
  return flattenVaultFiles(node.children ?? []);
}

/** Tree nodes to show in the center panel for a topic. */
export function treeForTopic(nodes: VaultNode[], topicPath: string | null): VaultNode[] {
  if (!topicPath) return nodes;
  const node = findNodeByPath(nodes, topicPath);
  if (!node) return [];
  if (node.type === "folder") return node.children ?? [];
  return [node];
}

export function recentInTopic(recentPaths: string[], topicPath: string | null): string[] {
  if (!topicPath) return recentPaths;
  const prefix = topicPath.endsWith("/") ? topicPath : `${topicPath}/`;
  return recentPaths.filter((p) => p === topicPath || p.startsWith(prefix));
}
