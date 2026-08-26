/** Pure helpers for editing a workspace folder (name, IDEA.md, subfolders). */

export const SYSTEM_SUBFOLDER_NAMES = new Set(["memory", "briefs", "watches", "research"]);

export function ideaBodyFromMarkdown(md: string): string {
  return md
    .replace(/^\uFEFF/, "")
    .replace(/^\s*#\s*Idea\s*(?:\r?\n)*/i, "")
    .trim();
}

export function ideaMarkdownFromBody(idea: string): string {
  const body = idea.trim();
  return body ? `# Idea\n\n${body}\n` : `# Idea\n\n`;
}

export function folderNameFromPath(path: string): string {
  return path.replace(/[/\\]+$/, "").split(/[/\\]/).pop() ?? "";
}

export function parentDir(path: string): string {
  const n = path.replace(/[/\\]+$/, "");
  const i = Math.max(n.lastIndexOf("/"), n.lastIndexOf("\\"));
  return i >= 0 ? n.slice(0, i) : n;
}

/**
 * Rewrite `path` when it is `from` or a descendant. Comparison is
 * case-insensitive; the replacement uses `to`'s casing.
 */
export function rewritePathPrefix(path: string, from: string, to: string): string {
  const src = from.replace(/[/\\]+$/, "");
  const dest = to.replace(/[/\\]+$/, "");
  if (!src || src.toLowerCase() === dest.toLowerCase()) return path;
  const lower = path.toLowerCase();
  const srcLower = src.toLowerCase();
  if (lower === srcLower) return dest;
  if (lower.startsWith(`${srcLower}/`) || lower.startsWith(`${srcLower}\\`)) {
    const rest = path.slice(src.length);
    if (rest === "/" || rest === "\\") return dest;
    return dest + rest;
  }
  return path;
}

export function isSystemSubfolder(name: string): boolean {
  return SYSTEM_SUBFOLDER_NAMES.has(name.toLowerCase());
}

/** Immediate child folder names the user may manage (not system or hidden). */
export function filterUserSubfolders(names: string[]): string[] {
  return names.filter((raw) => {
    const name = raw.trim();
    if (!name || name.startsWith(".")) return false;
    return !isSystemSubfolder(name);
  });
}
