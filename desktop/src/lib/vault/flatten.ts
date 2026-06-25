import type { VaultNode } from "./types";

export interface VaultFileRef {
  path: string;
  name: string;
}

export function flattenVaultFiles(nodes: VaultNode[]): VaultFileRef[] {
  const out: VaultFileRef[] = [];
  for (const node of nodes) {
    if (node.type === "file") {
      out.push({ path: node.path, name: node.name });
    }
    if (node.children) out.push(...flattenVaultFiles(node.children));
  }
  return out;
}