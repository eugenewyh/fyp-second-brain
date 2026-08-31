/** Workspace = topic folder; many Manager chats may share that memory. */

export const ONBOARD_OPENER =
  "Nothing saved in this topic yet. Ask anything — Nous checks memory first, then looks outside if needed. Paste notes to Teach when you want claims saved here.";

export function channelComposerPlaceholder(onboarding: boolean): string {
  if (onboarding) return "Ask anything — memory first, then outside sources…";
  return "Ask anything — memory first, then outside sources…";
}
