import { marked } from "marked";
import TurndownService from "turndown";
import { wikilinksToHtml } from "./wikilinks";

export interface NoteParts {
  frontmatter: string;
  body: string;
}

marked.setOptions({ gfm: true, breaks: false });

const turndown = new TurndownService({
  headingStyle: "atx",
  bulletListMarker: "-",
  codeBlockStyle: "fenced",
  emDelimiter: "*",
  strongDelimiter: "**",
});

turndown.addRule("wikiLink", {
  filter: (node: HTMLElement) =>
    node.nodeName === "A" && Boolean(node.getAttribute("data-wikilink")),
  replacement: (content: string, node: HTMLElement) => {
    const el = node;
    const target = el.getAttribute("data-wikilink") ?? "";
    const alias = content.trim();
    if (!target) return alias;
    if (alias === target) return `[[${target}]]`;
    return `[[${target}|${alias}]]`;
  },
});

turndown.addRule("strikethrough", {
  filter: ["del", "s"],
  replacement: (content: string) => `~~${content}~~`,
});

export function splitFrontmatter(content: string): NoteParts {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!match) return { frontmatter: "", body: content };
  return {
    frontmatter: match[0],
    body: content.slice(match[0].length),
  };
}

export function joinFrontmatter(parts: NoteParts): string {
  if (!parts.frontmatter) return parts.body;
  return `${parts.frontmatter}${parts.body}`;
}

/** Markdown body → HTML for TipTap (GFM via marked; wikilinks pre-expanded). */
export function markdownBodyToHtml(body: string): string {
  const withWiki = wikilinksToHtml(body.trim());
  const html = marked.parse(withWiki, { async: false }) as string;
  return html.trim();
}

/** TipTap HTML → markdown body (turndown with wikilink rule). */
export function htmlBodyToMarkdown(html: string): string {
  const md = turndown.turndown(html).trim();
  return md ? `${md}\n` : "";
}