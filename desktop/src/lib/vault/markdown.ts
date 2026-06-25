import { wikilinksInMarkdownToSyntax, wikilinksToHtml } from "./wikilinks";

export interface NoteParts {
  frontmatter: string;
  body: string;
}

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

/** Minimal markdown → HTML for TipTap load (headings, lists, paragraphs, wikilinks). */
export function markdownBodyToHtml(body: string): string {
  const withWiki = wikilinksToHtml(body);
  const lines = withWiki.split(/\r?\n/);
  const html: string[] = [];
  let inList = false;

  for (const line of lines) {
    if (line.startsWith("## ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h2>${line.slice(3)}</h2>`);
    } else if (line.startsWith("# ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h1>${line.slice(2)}</h1>`);
    } else if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${line.slice(2)}</li>`);
    } else if (line.trim() === "") {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
    } else {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<p>${line}</p>`);
    }
  }
  if (inList) html.push("</ul>");
  return html.join("");
}

/** Serialize TipTap HTML back to markdown body text. */
export function htmlBodyToMarkdown(html: string): string {
  let text = wikilinksInMarkdownToSyntax(html);
  text = text
    .replace(/<h1>([\s\S]*?)<\/h1>/gi, "# $1\n\n")
    .replace(/<h2>([\s\S]*?)<\/h2>/gi, "## $1\n\n")
    .replace(/<li>([\s\S]*?)<\/li>/gi, "- $1\n")
    .replace(/<\/?ul>/gi, "")
    .replace(/<p>([\s\S]*?)<\/p>/gi, "$1\n\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/?[^>]+>/g, "");
  return text.replace(/\n{3,}/g, "\n\n").trim() + "\n";
}