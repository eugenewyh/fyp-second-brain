export interface VaultNode {
  name: string;
  path: string;
  type: "folder" | "file";
  children?: VaultNode[];
}

export const VAULT_ROOT_LABEL = "data/documents/";