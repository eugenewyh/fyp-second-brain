export type ChatStarterId = "teach" | "ask" | "research" | "watch";

export type LandingPhase = "bootstrap" | "seed" | "ready";

export type ChatStarter = {
  id: ChatStarterId;
  verb: string;
  title: string;
  blurb: string;
  prompt: (topic: string) => string;
};

export type ChatSetupAction = "settings" | "ingest" | "workspace";

export type ChatSetupItem = {
  id: string;
  label: string;
  done: boolean;
  action?: ChatSetupAction;
};

export type LandingHero = {
  kicker: string;
  title: string;
  sub: string;
};

const GENERIC_TOPIC = "your project";

/** Topic label safe for starter prompts. */
export function topicForStarters(label: string): string {
  const t = label.trim();
  if (!t || t === "Choose topic" || t === "No workspace") return GENERIC_TOPIC;
  return t;
}

/** Empty-state starters aligned with capture → recall → autonomous research → watch. */
export const CHAT_STARTERS: ChatStarter[] = [
  {
    id: "teach",
    verb: "Teach",
    title: "Build memory",
    blurb: "Dump notes or files — consolidated into long-term claims",
    prompt: (topic) => `Here are my notes on ${topic}:\n\n`,
  },
  {
    id: "ask",
    verb: "Ask",
    title: "Recall",
    blurb: "Answer from what Nous already remembers in this topic",
    prompt: (topic) => `What do I already know about ${topic}?`,
  },
  {
    id: "research",
    verb: "Research",
    title: "Run agents",
    blurb: "Multi-agent research with sources; report writes back to memory",
    prompt: (topic) =>
      `Research the latest on ${topic}, verify sources, and file a report here`,
  },
  {
    id: "watch",
    verb: "Watch",
    title: "Stay current",
    blurb: "Autonomous briefs on a schedule — papers, launches, shifts",
    prompt: (topic) =>
      `Watch ${topic} for significant changes and brief me on weekday mornings`,
  },
];

export function landingPhase(opts: {
  offline: boolean;
  aiConfigured: boolean;
  hasWorkspace: boolean;
  libraryReady: boolean;
}): LandingPhase {
  if (opts.offline || !opts.aiConfigured || !opts.hasWorkspace) return "bootstrap";
  if (!opts.libraryReady) return "seed";
  return "ready";
}

export function landingHero(phase: LandingPhase): LandingHero {
  switch (phase) {
    case "bootstrap":
      return {
        kicker: "Get started",
        title: "Set up your second brain",
        sub: "Create a workspace, connect AI, and add documents. Nous needs something to remember before recall or research are useful.",
      };
    case "seed":
      return {
        kicker: "Second brain",
        title: "Give Nous something to remember",
        sub: "This workspace is empty — no indexed notes yet. Teach a dump, ingest files, or attach documents first.",
      };
    case "ready":
      return {
        kicker: "Second brain",
        title: "Long-term memory with autonomous agents",
        sub: "Nous recalls what you've taught it, runs multi-agent research when needed, and writes back — so the next session isn't a cold start.",
      };
  }
}

export function visibleStarterIds(phase: LandingPhase): ChatStarterId[] {
  switch (phase) {
    case "bootstrap":
      return [];
    case "seed":
      return ["teach"];
    case "ready":
      return ["teach", "ask", "research", "watch"];
  }
}

export function composerPlaceholder(phase: LandingPhase): string {
  switch (phase) {
    case "bootstrap":
      return "Complete setup to start…";
    case "seed":
      return "Teach Nous something about this workspace…";
    case "ready":
      return "Teach, ask from memory, or start research…";
  }
}

export function chatStarterPrompt(id: ChatStarterId, topicLabel: string): string {
  const topic = topicForStarters(topicLabel);
  const starter = CHAT_STARTERS.find((s) => s.id === id);
  return starter?.prompt(topic) ?? "";
}

export function chatSetupItems(opts: {
  offline: boolean;
  aiConfigured: boolean;
  hasWorkspace: boolean;
  libraryReady: boolean;
  memoryBlocked: boolean;
}): ChatSetupItem[] {
  const items: ChatSetupItem[] = [];

  if (opts.offline) {
    items.push({ id: "backend", label: "Start backend", done: false });
    return items;
  }

  if (!opts.hasWorkspace) {
    items.push({ id: "workspace", label: "Create workspace", done: false, action: "workspace" });
  }

  if (!opts.aiConfigured) {
    items.push({ id: "ai", label: "Add AI key", done: false, action: "settings" });
  }

  if (opts.hasWorkspace && !opts.libraryReady) {
    items.push({ id: "library", label: "Add documents", done: false, action: "ingest" });
  }

  if (opts.memoryBlocked) {
    items.push({
      id: "embeddings",
      label: "Fix memory search",
      done: false,
      action: "settings",
    });
  }

  return items;
}

export function chatSetupComplete(items: ChatSetupItem[]): boolean {
  return items.length === 0 || items.every((item) => item.done);
}
