import { htmlBodyToMarkdown, joinFrontmatter } from "$lib/vault/markdown";

/** Serialize TipTap editor HTML + frontmatter into a note file string (writeNote input). */
export function serializeEditorHtmlToNote(frontmatter: string, editorHtml: string): string {
  const body = htmlBodyToMarkdown(editorHtml);
  return joinFrontmatter({ frontmatter, body });
}