/** Persistent composer skills — label intent for the Manager (not separate apps). */

export type ComposerSkillId = "auto" | "teach" | "ask" | "research" | "watch";

export type ForcedJob = "file" | "answer" | "research" | "watch" | null;

export type ComposerSkill = {
  id: ComposerSkillId;
  label: string;
  /** Short hint under the chip when selected */
  hint: string;
  placeholder: string;
  job: ForcedJob;
};

export const COMPOSER_SKILLS: ComposerSkill[] = [
  {
    id: "auto",
    label: "Auto",
    hint: "Manager picks Teach, Ask, Research, or Watch",
    placeholder: "Teach, ask from memory, research, or schedule a watch…",
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
  {
    id: "watch",
    label: "Watch",
    hint: "Recurring research brief on a schedule",
    placeholder: "What should I watch and brief you on?",
    job: "watch",
  },
];

export function skillForJob(job: ForcedJob): ComposerSkill {
  return COMPOSER_SKILLS.find((s) => s.job === job) ?? COMPOSER_SKILLS[0]!;
}

export function skillPlaceholder(job: ForcedJob, fallback?: string): string {
  if (fallback?.trim()) return fallback;
  return skillForJob(job).placeholder;
}

export function forcedJobLabel(job: ForcedJob): string {
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
    title: "Then Ask — or Research / Watch",
    body: "Ask from remembered claims. Research looks outside and can write back. Watch briefs you on a schedule.",
  },
] as const;

export const THIN_MEMORY_REFUSE =
  "I don't have notes on this topic yet. Teach something here first — then Ask from what you saved.";
