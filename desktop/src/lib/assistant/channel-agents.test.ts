import { describe, expect, it } from "vitest";
import { ONBOARD_OPENER, channelComposerPlaceholder } from "./channel-agents";

describe("channel composer", () => {
  it("has an empty-channel opener", () => {
    expect(ONBOARD_OPENER).toMatch(/nothing saved/i);
    expect(ONBOARD_OPENER).toMatch(/memory first/i);
  });

  it("uses ask-first placeholder when empty", () => {
    expect(channelComposerPlaceholder(true)).toMatch(/Ask anything/i);
    expect(channelComposerPlaceholder(false)).toMatch(/memory first/i);
  });
});
