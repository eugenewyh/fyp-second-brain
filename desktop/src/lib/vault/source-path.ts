import type { VaultFileRef } from "./flatten";
import { resolveSemanticSourcePath } from "./search-dispatch";

/**
 * Map a citation / retrieval label to a real vault file.
 * Never invent `{vaultRoot}/{label}` — that opens a path that does not exist
 * when the label is `Personal — notes.md`.
 */
export function resolveSourcePath(
  source: string,
  _vaultRoot: string | null,
  vaultFiles: VaultFileRef[] = [],
): string | null {
  if (!source.trim() || !vaultFiles.length) return null;
  return resolveSemanticSourcePath(source, vaultFiles);
}
