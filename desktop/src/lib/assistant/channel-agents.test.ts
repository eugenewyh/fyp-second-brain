import { describe, expect, it } from "vitest";
import { ONBOARD_OPENER, channelComposerPlaceholder } from "./channel-agents";

describe("channel composer", () => {
  it("has an empty-channel opener", () => {
    expect(ONBOARD_OPENER).toMatch(/nothing in memory/i);
    expect(ONBOARD_OPENER).toMatch(/Teach/i);
  });

  it("uses teach-first placeholder when empty", () => {
    expect(channelComposerPlaceholder(true)).toMatch(/Teach/i);
    expect(channelComposerPlaceholder(false)).toMatch(/ask from memory/i);
  });
});
