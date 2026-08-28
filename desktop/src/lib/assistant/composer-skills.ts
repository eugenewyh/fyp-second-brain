/** Persistent composer skills — label intent for the Manager (not separate apps). */

export type ComposerSkillId = "auto" | "teach" | "ask" | "research";

export type ForcedJob = "file" | "answer" | "research" | "watch" | null;

export type ComposerSkill = {
  id: ComposerSkillId;
  label: string;
  /** Short hint under the chip when selected */
  hint: string;
  placeholder: string;
  job: Exclude<ForcedJob, "watch">;
};

export const COMPOSER_SKILLS: ComposerSkill[] = [
  {
    id: "auto",
    label: "Auto",
    hint: "Manager picks Teach, Ask, or Research",
    placeholder: "Teach, ask from memory, or research…",
    job: null,
  },
  {
    id: "teach",
    label: "Teach",
    hint: "Paste notes or attach files to remember",
    placeholder: "Paste notes or attach files to remember…",
    job: "file",
  },
  {
    id: "ask",
    label: "Ask",
    hint: "Answer only from what this topic remembers",
    placeholder: "Ask from what this topic already remembers…",
    job: "answer",
  },
  {
    id: "research",
    label: "Research",
    hint: "Look up sources; report can write back to memory",
    placeholder: "What should I investigate and file here?",
    job: "research",
  },
];

export function skillForJob(job: ForcedJob): ComposerSkill {
  if (job === "watch") return COMPOSER_SKILLS[0]!;
  return COMPOSER_SKILLS.find((s) => s.job === job) ?? COMPOSER_SKILLS[0]!;
}

export function skillPlaceholder(job: ForcedJob, fallback?: string): string {
  if (fallback?.trim()) return fallback;
  return skillForJob(job).placeholder;
}

export function forcedJobLabel(job: ForcedJob): string {
  if (job === "watch") return "Research";
  return skillForJob(job).label;
}

/** Empty-topic coach steps (first-run / seed phase). */
export const COACH_STEPS = [
  {
    n: "1",
    title: "This chat belongs to a topic",
    body: "A topic is your knowledge folder — Coffee, FYP, Plants. Everything you teach stays there.",
  },
  {
    n: "2",
    title: "Teach first",
    body: "Paste notes or add files. Files on the shelf are not memory until Teach turns them into claims.",
  },
  {
    n: "3",
    title: "Then Ask — or Research",
    body: "Ask from remembered claims. Research looks outside and can write back. For recurring briefs, use Scheduled Research in the sidebar.",
  },
] as const;

export const THIN_MEMORY_REFUSE =
  "I don't have notes on this topic yet. Teach something here first — then Ask from what you saved.";
