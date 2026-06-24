import { invoke } from "@tauri-apps/api/core";
import { api } from "$lib/api";
import { type VaultNode, VAULT_ROOT_LABEL } from "./types";

/** Load vault tree from Tauri (reads project data/documents/ on disk). */
export async function loadVaultTree(): Promise<VaultNode[]> {
  try {
    const nodes = await invoke<VaultNode[]>("list_vault_tree");
    if (nodes.length > 0) return nodes;
  } catch {
    /* fall through to status-based root */
  }

  try {
    const status = await api.status();
    return [
      {
        name: VAULT_ROOT_LABEL,
        path: `${status.project_root}/data/documents`,
        type: "folder",
        children: [],
      },
    ];
  } catch {
    return [
      {
        name: VAULT_ROOT_LABEL,
        path: "data/documents",
        type: "folder",
        children: [],
      },
    ];
  }
}

/** Filter vault nodes by fuzzy query (case-insensitive substring match). */
export function filterVaultTree(nodes: VaultNode[], query: string): VaultNode[] {
  const q = query.trim().toLowerCase();
  if (!q) return nodes;

  function matchNode(node: VaultNode): VaultNode | null {
    const selfMatch = node.name.toLowerCase().includes(q);
    const childMatches = (node.children ?? [])
      .map(matchNode)
      .filter((n): n is VaultNode => n !== null);

    if (selfMatch || childMatches.length > 0) {
      return { ...node, children: childMatches.length ? childMatches : node.children };
    }
    return null;
  }

  return nodes.map(matchNode).filter((n): n is VaultNode => n !== null);
}