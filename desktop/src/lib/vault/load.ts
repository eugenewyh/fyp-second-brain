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

/** True when fuzzy filter excluded all nodes but the vault itself has files. */
export function isVaultFilterEmpty(nodes: VaultNode[], filtered: VaultNode[]): boolean {
  return !isVaultTreeEmpty(nodes) && filtered.length === 0;
}

/** True when vault has no files (root only or empty). */
export function isVaultTreeEmpty(nodes: VaultNode[]): boolean {
  if (nodes.length === 0) return true;
  if (nodes.length === 1) {
    const children = nodes[0].children;
    return !children || children.length === 0;
  }
  return false;
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

    if (childMatches.length > 0) {
      return { ...node, children: childMatches };
    }
    if (selfMatch) {
      return { ...node, children: node.children };
    }
    return null;
  }

  return nodes.map(matchNode).filter((n): n is VaultNode => n !== null);
}