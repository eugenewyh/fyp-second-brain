/** Convert markdown-ish research report text to simple HTML for display. */
export function renderReport(md: string): string {
  return md
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/^(.+)$/gm, (line) => {
      if (line.startsWith("<h2>") || line.startsWith("<li>")) return line;
      return line;
    });
}