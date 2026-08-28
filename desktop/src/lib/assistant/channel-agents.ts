/** Workspace = topic folder; many Manager chats may share that memory. */

export const ONBOARD_OPENER =
  "This topic has nothing in memory yet. Teach notes or files first — then Ask from what I remember, or Research to look outside. Recurring briefs live in Scheduled Research.";

export function channelComposerPlaceholder(onboarding: boolean): string {
  if (onboarding) return "Paste notes or attach files to Teach this topic…";
  return "Teach, ask from memory, or research…";
}
