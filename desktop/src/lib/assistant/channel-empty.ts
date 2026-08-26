import { ideaBodyFromMarkdown } from "$lib/vault/project-edit";
import { isRememberableNotePath } from "$lib/vault/rememberable";

/** Pure emptiness check used by tests and after a disk walk. */
export function channelLooksEmpty(opts: {
  idea: string;
  claimCount: number;
  notePaths: string[];
}): boolean {
  if (opts.idea.trim()) return false;
  if (opts.claimCount > 0) return false;
  return !opts.notePaths.some((p) => isRememberableNotePath(p));
}

export function ideaBodyFromFile(md: string): string {
  return ideaBodyFromMarkdown(md);
}
