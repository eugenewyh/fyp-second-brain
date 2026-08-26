/** Parse and render research reports (Elicit-inspired structure). */

export interface ReportSection {
  id: string;
  title: string;
  body: string;
}

export interface ReportSourceRow {
  index: number;
  label: string;
  origin?: string;
}

const HEADING_RE = /^##\s+(.+)$/gm;

export function parseReportSections(md: string): ReportSection[] {
  if (!md.trim()) return [];
  const sections: ReportSection[] = [];
  const matches = [...md.matchAll(HEADING_RE)];
  if (matches.length === 0) {
    return [{ id: "body", title: "Report", body: md.trim() }];
  }
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    const title = m[1].trim();
    const start = (m.index ?? 0) + m[0].length;
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? md.length) : md.length;
    const body = md.slice(start, end).trim();
    const id = slugify(title);
    sections.push({ id, title, body });
  }
  return sections;
}

export function slugify(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48) || "section";
}

/** Map academic or legacy headings to everyday titles for display. */
export function displayReportTitle(title: string): string {
  const t = title.trim();
  if (/^in short$/i.test(t) || /executive\s+summary/i.test(t) || /^\s*summary\s*$/i.test(t)) {
    return "In short";
  }
  if (/^what we found$/i.test(t) || /key\s+findings/i.test(t) || /^\s*findings\s*$/i.test(t)) {
    return "What we found";
  }
  if (/^the details$/i.test(t) || /detailed\s+analysis/i.test(t)) {
    return "The details";
  }
  if (/^what'?s missing$/i.test(t) || /identified\s+gaps/i.test(t)) {
    return "What's missing";
  }
  return t;
}

export function isLeadSectionTitle(title: string): boolean {
  const shown = displayReportTitle(title);
  return shown === "In short" || shown === "What we found";
}

export function isFindingsSectionTitle(title: string): boolean {
  return displayReportTitle(title) === "What we found";
}

/** Extract bullet findings from What we found / Key Findings. */
export function extractKeyFindings(md: string, max = 8): string[] {
  const sections = parseReportSections(md);
  const findings =
    sections.find((s) => isFindingsSectionTitle(s.title)) ??
    sections.find((s) => displayReportTitle(s.title) === "In short");
  if (!findings) return [];
  return findings.body
    .split("\n")
    .map((l) => l.replace(/^[\s>*\-•\d.]+/, "").trim())
    .filter((l) => l.length > 12 && l.length < 280)
    .slice(0, max);
}

/** Parse Sources section into rows. */
export function parseSourcesSection(md: string): ReportSourceRow[] {
  const sections = parseReportSections(md);
  const sources = sections.find((s) => /^sources?/i.test(s.title));
  if (!sources) return [];
  const rows: ReportSourceRow[] = [];
  for (const line of sources.body.split("\n")) {
    const m = line.match(/^\[(\d+)\]\s*(.+)$/);
    if (!m) continue;
    const label = m[2].trim();
    let origin: string | undefined;
    if (/^personal/i.test(label) || /—\s*personal/i.test(label)) origin = "personal";
    else if (/^notion/i.test(label) || /notion\.so/i.test(label)) origin = "notion";
    else if (/arxiv/i.test(label)) origin = "arxiv";
    else if (/^web/i.test(label) || /https?:\/\//i.test(label)) origin = "web";
    rows.push({ index: Number(m[1]), label, origin });
  }
  return rows;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function renderInline(md: string, citeTitles?: Map<number, string>): string {
  return md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\[(\d+)\]/g, (_m, n: string) => {
      const title = citeTitles?.get(Number(n));
      const t = title ? ` title="${escapeHtml(title)}"` : "";
      return `<sup class="cite" data-cite="${n}" role="button" tabindex="0"${t}>[${n}]</sup>`;
    })
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

export function renderSectionBody(body: string, citeTitles?: Map<number, string>): string {
  const lines = body.split("\n");
  const out: string[] = [];
  let inList = false;
  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = line.match(/^[-*•]\s+(.+)$/) || line.match(/^\d+[.)]\s+(.+)$/);
    if (bullet) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${renderInline(bullet[1], citeTitles)}</li>`);
      continue;
    }
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
    if (!line.trim()) continue;
    out.push(`<p>${renderInline(line.trim(), citeTitles)}</p>`);
  }
  if (inList) out.push("</ul>");
  return out.join("\n");
}

/** Legacy helper used by older call sites. */
export function renderReport(md: string): string {
  const sections = parseReportSections(md);
  if (sections.length === 1 && sections[0].id === "body") {
    return renderSectionBody(md);
  }
  return sections
    .map((s) => `<h2 id="${s.id}">${escapeHtml(s.title)}</h2>\n${renderSectionBody(s.body)}`)
    .join("\n");
}
