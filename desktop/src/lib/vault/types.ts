export type VaultNodeType = "file" | "folder";

export interface VaultNode {
  name: string;
  path: string;
  type: VaultNodeType;
  children?: VaultNode[];
}

export interface VaultSearchHit {
  path: string;
  name: string;
  score: number;
  excerpt?: string;
}