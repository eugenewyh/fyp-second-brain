import { describe, expect, it } from "vitest";
import {
  CHAT_STARTERS,
  chatSetupItems,
  chatStarterPrompt,
  landingHero,
  landingPhase,
  topicForStarters,
  visibleStarterIds,
} from "./chat-starters";

describe("topicForStarters", () => {
  it("uses the workspace label when set", () => {
    expect(topicForStarters("Skunkworks")).toBe("Skunkworks");
  });

  it("falls back for empty or placeholder labels", () => {
    expect(topicForStarters("")).toBe("your project");
    expect(topicForStarters("Choose topic")).toBe("your project");
  });
});

describe("landingPhase", () => {
  it("bootstraps when offline, missing AI, or no workspace", () => {
    expect(
      landingPhase({
        offline: true,
        aiConfigured: true,
        hasWorkspace: true,
        libraryReady: true,
      }),
    ).toBe("bootstrap");
    expect(
      landingPhase({
        offline: false,
        aiConfigured: false,
        hasWorkspace: true,
        libraryReady: true,
      }),
    ).toBe("bootstrap");
    expect(
      landingPhase({
        offline: false,
        aiConfigured: true,
        hasWorkspace: false,
        libraryReady: true,
      }),
    ).toBe("bootstrap");
  });

  it("seeds when connected but library is empty", () => {
    expect(
      landingPhase({
        offline: false,
        aiConfigured: true,
        hasWorkspace: true,
        libraryReady: false,
      }),
    ).toBe("seed");
  });

  it("seeds when this workspace is empty even if the library has content", () => {
    expect(
      landingPhase({
        offline: false,
        aiConfigured: true,
        hasWorkspace: true,
        libraryReady: true,
        channelEmpty: true,
      }),
    ).toBe("seed");
  });

  it("is ready when workspace, AI, and library exist", () => {
    expect(
      landingPhase({
        offline: false,
        aiConfigured: true,
        hasWorkspace: true,
        libraryReady: true,
      }),
    ).toBe("ready");
  });
});

describe("visibleStarterIds", () => {
  it("leads empty topics with Teach; full set when ready", () => {
    expect(visibleStarterIds("bootstrap")).toEqual([]);
    expect(visibleStarterIds("seed")).toEqual(["teach"]);
    expect(visibleStarterIds("ready")).toEqual(["teach", "ask", "research"]);
  });
});

describe("landingHero", () => {
  it("explains setup before chat on bootstrap", () => {
    expect(landingHero("bootstrap").title).toContain("Set up");
  });

  it("teaches the Teach → Ask loop on seed", () => {
    expect(landingHero("seed").title).toContain("Teach");
    expect(landingHero("seed").sub.toLowerCase()).toContain("memory");
  });
});

describe("chatStarterPrompt", () => {
  it("fills teach / ask / research templates", () => {
    expect(chatStarterPrompt("ask", "FYP")).toContain("FYP");
    expect(chatStarterPrompt("research", "FYP")).toContain("file a report");
    expect(chatStarterPrompt("teach", "FYP")).toContain("Here are my notes");
  });
});

describe("chatSetupItems", () => {
  it("prioritizes backend when offline", () => {
    const items = chatSetupItems({
      offline: true,
      aiConfigured: false,
      hasWorkspace: false,
      libraryReady: false,
      memoryBlocked: false,
    });
    expect(items).toHaveLength(1);
    expect(items[0]?.id).toBe("backend");
  });

  it("lists workspace and AI before library on greenfield", () => {
    const items = chatSetupItems({
      offline: false,
      aiConfigured: false,
      hasWorkspace: false,
      libraryReady: false,
      memoryBlocked: false,
    });
    expect(items.map((i) => i.id)).toEqual(["workspace", "ai"]);
  });

  it("offers Import notes when this workspace is empty", () => {
    const items = chatSetupItems({
      offline: false,
      aiConfigured: true,
      hasWorkspace: true,
      libraryReady: true,
      channelEmpty: true,
      memoryBlocked: false,
    });
    expect(items.map((i) => i.id)).toEqual(["import"]);
    expect(items[0]?.action).toBe("import");
  });
});

describe("CHAT_STARTERS", () => {
  it("covers capture, recall, and autonomous research", () => {
    expect(CHAT_STARTERS.map((s) => s.id)).toEqual([
      "teach",
      "ask",
      "research",
    ]);
  });
});
