import type { VaultFileRef } from "./flatten";
import { resolveSemanticSourcePath } from "./search-dispatch";

export function resolveSourcePath(
  source: string,
  vaultRoot: string | null,
  vaultFiles: VaultFileRef[] = [],
): string | null {
  if (vaultFiles.length) {
    const resolved = resolveSemanticSourcePath(source, vaultFiles);
    if (resolved) return resolved;
  }
  if (!vaultRoot) return null;
  const base = source.split("/").pop() ?? source;
  return `${vaultRoot}/${base}`;
}