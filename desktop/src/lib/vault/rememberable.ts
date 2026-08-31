import { shouldSkipWatcherIngest } from "./watcher-skip";

const SKIP_BASENAMES = new Set(["instruction.md", "idea.md", "readme.md"]);

/** Notes the user meant to keep — not Watch/Teach traces or starter stubs. */
export function isRememberableNotePath(path: string): boolean {
  if (shouldSkipWatcherIngest(path)) return false;
  const name = path.split(/[\\/]/).pop()?.toLowerCase() ?? "";
  if (SKIP_BASENAMES.has(name)) return false;
  return /\.(md|txt|pdf|docx)$/i.test(name);
}
