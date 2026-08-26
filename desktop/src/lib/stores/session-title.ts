/** Session sidebar titles derived from thread content. */

export const SESSION_TITLE_MAX = 36;
export const SESSION_TITLE_WORDS = 5;
export const DEFAULT_SESSION_TITLE = "New Chat";

const PLACEHOLDER_TITLES = new Set([
  "",
  "new chat",
  "new research",
  "migrated session",
  "chat",
]);

/** Strip chatty lead-ins so titles read like short topics. */
const LEAD =
  /^(?:please\s+)?(?:hey\s+|hi\s+|hello\s+)?(?:can\s+you\s+|could\s+you\s+|would\s+you\s+)?(?:please\s+)?(?:help\s+(?:me\s+)?(?:with\s+|to\s+)?|tell\s+me\s+|show\s+me\s+|give\s+me\s+|find\s+(?:me\s+)?|search(?:\s+for)?\s+|look\s*up\s+|watch(?:\s+for)?\s+|research\s+|read(?:\s+about)?\s+|summarise\s+|summarize\s+|explain\s+|describe\s+|what(?:'s|s|\s+is|\s+are|\s+do\s+i|\s+does|\s+did\s+i|\s+should(?:\s+i)?|\s+can(?:\s+i)?|\s+will(?:\s+i)?)?\s+(?:my\s+|the\s+|a\s+|an\s+)?|according\s+to\s+(?:my\s+)?(?:notes?|memory|vault)\s*,?\s*(?:what|how|when|where|why|who)?\s*(?:do\s+i\s+|did\s+i\s+|is\s+|are\s+|was\s+|were\s+)?|based\s+on\s+(?:my\s+)?(?:notes?|memory)\s*,?\s*)/i;

const FILLER_TAIL =
  /\b(?:please|thanks|thank\s+you|for\s+me|right\s+now|today)\s*$/i;

export type SessionTitleTurn = {
  kind: string;
  content?: string;
  query?: string;
  label?: string;
};

export function isPlaceholderSessionTitle(
  title: string,
  folderName?: string | null,
): boolean {
  const t = title.trim();
  if (!t || PLACEHOLDER_TITLES.has(t.toLowerCase())) return true;
  const folder = folderName?.trim();
  if (folder && t.toLowerCase() === folder.toLowerCase()) return true;
  return false;
}

/** True when the title was clearly auto-truncated (safe to re-derive). */
export function isTruncatedAutoTitle(title: string): boolean {
  return title.trim().endsWith("…");
}

export function truncateSessionTitle(text: string, max = SESSION_TITLE_MAX): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

/** Normalize a model-proposed title; null if unusable. */
export function normalizeLlmSessionTitle(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;
  let text = raw.trim().split("\n")[0] ?? "";
  text = text.replace(/^["'`“”‘’]+|["'`“”‘’]+$/g, "").trim();
  text = text.replace(/^title\s*:\s*/i, "").trim();
  text = text.replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim();
  text = text.replace(/[?.!,;:]+$/g, "").trim();
  if (text.length < 2) return null;
  const words = text.split(" ").filter(Boolean);
  if (!words.length) return null;
  let clipped = words.slice(0, SESSION_TITLE_WORDS + 1).join(" ");
  if (clipped.length > SESSION_TITLE_MAX) {
    clipped =
      clipped.slice(0, SESSION_TITLE_MAX).replace(/\s+\S*$/, "") ||
      clipped.slice(0, SESSION_TITLE_MAX);
  }
  const lower = clipped.toLowerCase();
  if (PLACEHOLDER_TITLES.has(lower) || lower === "untitled" || lower === "title" || lower === "n/a") {
    return null;
  }
  return truncateSessionTitle(clipped);
}

/** True when an LLM rename is allowed to overwrite the current title. */
export function canApplyLlmSessionTitle(
  current: string,
  folderName?: string | null,
  heuristic?: string | null,
): boolean {
  if (isPlaceholderSessionTitle(current, folderName)) return true;
  if (isTruncatedAutoTitle(current)) return true;
  if (heuristic && current.trim() === heuristic.trim()) return true;
  return false;
}

/** Strip attachment footnotes from a user bubble before using it as a title. */
function cleanUserTitleSource(content: string): string {
  return content.replace(/\n\nAttached \(this question only\):.*$/s, "").trim();
}

/**
 * Cursor-style short label: strip lead-ins, keep ~3–5 words, title-case lightly.
 */
export function phraseTitleFromText(text: string): string | null {
  let blob = cleanUserTitleSource(text).split("\n")[0] ?? "";
  blob = blob.replace(/[?.!]+$/g, "").trim();
  if (!blob) return null;

  // Drop leading @mentions / slash commands that aren't useful alone.
  if (/^\/\S+$/.test(blob) || blob.length < 3) return null;

  blob = blob.replace(LEAD, "").trim();
  blob = blob.replace(FILLER_TAIL, "").trim();
  blob = blob.replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim();
  blob = blob.replace(/[?.!,;:]+$/g, "").trim();

  const words = blob.split(" ").filter(Boolean);
  if (!words.length) return null;

  let clipped = words.slice(0, SESSION_TITLE_WORDS).join(" ");
  if (clipped.length > SESSION_TITLE_MAX) {
    clipped =
      clipped.slice(0, SESSION_TITLE_MAX).replace(/\s+\S*$/, "") ||
      clipped.slice(0, SESSION_TITLE_MAX);
  }

  const lower = clipped.toLowerCase();
  if (["this", "it", "help", "please", "stuff", "that", "something"].includes(lower)) {
    return null;
  }

  return truncateSessionTitle(titleCasePhrase(clipped));
}

function titleCasePhrase(text: string): string {
  const small = new Set([
    "a",
    "an",
    "the",
    "and",
    "or",
    "for",
    "of",
    "on",
    "in",
    "to",
    "my",
    "vs",
  ]);
  return text
    .split(" ")
    .map((w, i) => {
      const upperCount = (w.match(/[A-Z]/g) ?? []).length;
      if (upperCount >= 2) return w; // keep acronyms like DLMs, LLMs, FYP
      const lower = w.toLowerCase();
      if (i > 0 && small.has(lower)) return lower;
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

/**
 * Prefer a short phrase from the first user message, then research / digest.
 */
export function titleFromSessionTurns(turns: SessionTitleTurn[]): string | null {
  for (const t of turns) {
    if (t.kind === "user" && t.content?.trim()) {
      const phrase = phraseTitleFromText(t.content);
      if (phrase) return phrase;
    }
  }
  for (const t of turns) {
    if (t.kind === "research" && t.query?.trim()) {
      return phraseTitleFromText(t.query) ?? truncateSessionTitle(t.query);
    }
    if (t.kind === "digest" && t.label?.trim()) {
      return phraseTitleFromText(t.label) ?? truncateSessionTitle(t.label);
    }
  }
  return null;
}
