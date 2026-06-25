import { resolveWikilinkTarget } from "$lib/vault/wikilinks";
import type { VaultFileRef } from "$lib/vault/flatten";

/** Resolve a clicked wikilink target against the current vault file index. */
export function activateWikilinkTarget(
  dataWikilink: string,
  vaultFiles: VaultFileRef[],
): string | null {
  return resolveWikilinkTarget(dataWikilink, vaultFiles);
}