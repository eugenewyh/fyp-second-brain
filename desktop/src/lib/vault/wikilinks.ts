export interface ParsedWikilink {
  full: string;
  target: string;
  alias: string;
}

export const WIKILINK_PATTERN = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g;

export function parseWikilinks(text: string): ParsedWikilink[] {
  const results: ParsedWikilink[] = [];
  for (const match of text.matchAll(WIKILINK_PATTERN)) {
    const target = match[1].trim();
    const alias = (match[2] ?? target).trim();
    results.push({ full: match[0], target, alias });
  }
  return results;
}

export function normalizeNoteName(name: string): string {
  return name.replace(/\.md$/i, "").trim().toLowerCase();
}

export function resolveWikilinkTarget(
  target: string,
  files: { path: string; name: string }[],
): string | null {
  const want = normalizeNoteName(target);
  const exact = files.find((f) => normalizeNoteName(f.name) === want);
  if (exact) return exact.path;
  const partial = files.find((f) => normalizeNoteName(f.name).includes(want));
  return partial?.path ?? null;
}

export function wikilinksToHtml(text: string): string {
  return text.replace(WIKILINK_PATTERN, (_full, target: string, alias?: string) => {
    const label = (alias ?? target).trim();
    const t = target.trim();
    return `<a data-wikilink="${escapeAttr(t)}" class="wikilink">${escapeHtml(label)}</a>`;
  });
}

export function wikilinksInMarkdownToSyntax(html: string): string {
  return html.replace(
    /<a[^>]*data-wikilink="([^"]*)"[^>]*>([^<]*)<\/a>/gi,
    (_m, target: string, label: string) => {
      const t = decodeAttr(target);
      const l = decodeHtml(label);
      if (l === t) return `[[${t}]]`;
      return `[[${t}|${l}]]`;
    },
  );
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

function decodeAttr(s: string): string {
  return s.replace(/&quot;/g, '"').replace(/&amp;/g, "&");
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function decodeHtml(s: string): string {
  return s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}