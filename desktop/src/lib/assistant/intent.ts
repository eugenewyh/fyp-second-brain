export type TurnIntent = "teach" | "explain" | "lookup";

const LOOKUP_RE =
  /\b(look\s*up|looking\s*up|find\s+papers?|arxiv|search\s+the\s+web|what'?s\s+new|latest)\b/i;

/** Mission-style research (Research chip, "Research …", compare/write-up phrasing). */
const RESEARCH_INTENT_RE =
  /(?:^\s*research\b)|(?:\b(?:investigate|explore|survey|deep\s+dive|write\s+(?:a\s+)?report)\b)|(?:\b(?:file\s+(?:a\s+)?report|compile\s+(?:a\s+)?report|run\s+(?:a\s+)?report)\b)|(?:\b(?:find\s+sources|gather\s+sources|source\s+review)\b)|(?:\b(?:pros\s+and\s+cons|state\s+of\s+the\s+art|literature\s+review)\b)|(?:\b(?:compare|contrast)\s+.+\s+(?:vs\.?|versus|and)\b)|(?:\b(?:what\s+(?:are|is)\s+(?:the\s+)?(?:latest|current|recent))\b)/i;

const SYNTHESIS_RE =
  /\b(synthesi[sz]e|synthesis|stance\s+on|write[- ]?up|literature\s+review|report\s+on|multi[- ]?part)\b/i;

const NOTES_RE =
  /\b(according to my notes|in my notes|from my notes|my notes say|based on my notes|from my library|cite my notes)\b/i;

const LEARN_RE =
  /\b(teach\s+me(?:\s+everything)?\s+about|teach(?:\s+me)?\s+(?:everything\s+)?about|walk\s+me\s+through|help\s+me\s+(?:understand|learn)(?:\s+about|\s+what|\s+how|\s+why|\s+the|\s+everything|\s+all|\s+\w|$)|explain\s+(?:to\s+me\s+)?(?:everything\s+)?about)\b/i;

const QUESTION_START =
  /^(what|why|how|when|where|who|which|does|do|did|is|are|can|could|should|would|explain|summarise|summarize|synthesi[sz]e|compare)\b/i;

export function hasLookupVerbs(text: string): boolean {
  return LOOKUP_RE.test(text.trim());
}

export function hasResearchIntent(text: string): boolean {
  return RESEARCH_INTENT_RE.test(text.trim());
}

/** User already asked to look outside — never show static refuse + extra Look up step. */
export function shouldAutoResearch(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  return hasResearchIntent(t) || hasLookupVerbs(t) || hasSynthesisIntent(t);
}

export function hasSynthesisIntent(text: string): boolean {
  return SYNTHESIS_RE.test(text.trim());
}

export function hasNotesIntent(text: string): boolean {
  return NOTES_RE.test(text.trim());
}

export function hasLearnIntent(text: string): boolean {
  return LEARN_RE.test(text.trim());
}

export function isQuestion(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  if (t.includes("?")) return true;
  return QUESTION_START.test(t);
}

/** Long note-like paste with no question — teach. Short accidental paste is not a dump. */
export function isNoteDump(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  if (hasLookupVerbs(t) || isQuestion(t) || hasSynthesisIntent(t) || hasLearnIntent(t)) return false;
  const paragraphs = t.split(/\n\s*\n/).filter((p) => p.trim().length > 40);
  return t.length >= 800 || paragraphs.length >= 3;
}

export function classifyIntent(opts: {
  text: string;
  hasAttachments?: boolean;
}): TurnIntent {
  if (opts.hasAttachments) return "teach";
  const text = opts.text.trim();
  if (isNoteDump(text)) return "teach";
  // Synthesis over notes → research (lookup), not plain explain
  if (hasSynthesisIntent(text)) return "lookup";
  if (hasNotesIntent(text) || hasLearnIntent(text)) return "explain";
  if (hasLookupVerbs(text) || hasResearchIntent(text)) return "lookup";
  return "explain";
}

/** After filing attachments/dumps, optionally continue with a question. */
export function leftoverQuestionAfterTeach(text: string): string | null {
  const t = text.trim();
  if (!t) return null;
  if (isNoteDump(t) && !isQuestion(t) && !hasLookupVerbs(t)) return null;
  if (isQuestion(t) || hasLookupVerbs(t) || hasSynthesisIntent(t)) return t;
  return null;
}
