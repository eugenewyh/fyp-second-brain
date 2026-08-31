/** Classify where a source came from for UI differentiation vs generic chatbots. */

export type SourceOrigin = "personal" | "web" | "arxiv" | "notion" | "past_research" | "unknown";

export function classifySourceOrigin(source: string): SourceOrigin {
  const s = (source || "").toLowerCase();
  if (!s) return "unknown";
  if (s.includes("/research/") || s.includes("research\\") || s.includes("type: research")) {
    return "past_research";
  }
  if (s.includes("arxiv") || s.includes("arxiv.org")) return "arxiv";
  if (s.includes("notion.so") || s.startsWith("notion ") || s.startsWith("notion—") || s.startsWith("notion –")) {
    return "notion";
  }
  if (
    s.startsWith("http://") ||
    s.startsWith("https://") ||
    s.includes("tavily") ||
    s.startsWith("www.")
  ) {
    return "web";
  }
  // Local vault paths / filenames
  if (s.includes("/") || s.includes("\\") || /\.(md|pdf|txt|docx)$/i.test(s)) {
    return "personal";
  }
  return "unknown";
}

export function originLabel(origin: SourceOrigin): string {
  switch (origin) {
    case "personal":
      return "Your library";
    case "web":
      return "Web";
    case "arxiv":
      return "arXiv";
    case "notion":
      return "Notion";
    case "past_research":
      return "Past research";
    default:
      return "Source";
  }
}

export function originShort(origin: SourceOrigin): string {
  switch (origin) {
    case "personal":
      return "Personal";
    case "web":
      return "Web";
    case "arxiv":
      return "arXiv";
    case "notion":
      return "Notion";
    case "past_research":
      return "Past research";
    default:
      return "Source";
  }
}

/**
 * Report bibliography lines look like `Personal — notes.md, p.12`.
 * Return the file or URL part used to open the source.
 */
export function sourceLookupName(source: string): string {
  let s = (source || "").trim();
  s = s.replace(/^(personal|web|arxiv|notion|past research)\s*[—–-]\s*/i, "");
  s = s.replace(/,?\s*p(?:age)?\.?\s*\d+\s*$/i, "");
  return s.trim();
}

export function sourceDisplayName(source: string): string {
  if (!source) return "Unknown";
  try {
    if (source.startsWith("http")) {
      const u = new URL(source);
      return u.hostname.replace(/^www\./, "") + u.pathname.slice(0, 40);
    }
  } catch {
    /* ignore */
  }
  return source.split(/[\\/]/).pop() ?? source;
}
