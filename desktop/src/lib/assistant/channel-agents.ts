/** Workspace = topic folder; many Manager chats may share that memory. */

export const ONBOARD_OPENER =
  "This workspace has nothing in memory yet. What is it for — notes you already have, or research you want run?";

export function channelComposerPlaceholder(onboarding: boolean): string {
  if (onboarding) return "Reply to set up this workspace…";
  return "Message this workspace…";
}
