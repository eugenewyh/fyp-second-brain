import { describe, expect, it } from "vitest";
import { ONBOARD_OPENER, channelComposerPlaceholder } from "./channel-agents";

describe("channel composer", () => {
  it("has an empty-channel opener", () => {
    expect(ONBOARD_OPENER).toMatch(/nothing in memory/i);
  });

  it("uses onboarding placeholder when empty", () => {
    expect(channelComposerPlaceholder(true)).toMatch(/set up/i);
    expect(channelComposerPlaceholder(false)).toMatch(/Message this workspace/i);
  });
});
