import { describe, expect, it } from "vitest";
import {
  isIdleSession,
  sessionHasDraft,
  shouldDiscardIdleSession,
  type AssistantTurn,
} from "$lib/stores/assistant.svelte";

const blank: AssistantTurn[] = [];
const openerOnly: AssistantTurn[] = [
  { id: "1", kind: "manager", content: "Hey." },
];
const withUser: AssistantTurn[] = [
  { id: "1", kind: "manager", content: "Hey." },
  { id: "2", kind: "user", content: "How do I make espresso?" },
];

describe("isIdleSession", () => {
  it("treats blank and opener-only chats as idle", () => {
    expect(isIdleSession({ turns: blank })).toBe(true);
    expect(isIdleSession({ turns: openerOnly })).toBe(true);
  });

  it("keeps chats that have a user message", () => {
    expect(isIdleSession({ turns: withUser })).toBe(false);
  });

  it("treats Remember / digest turns as real work, not New Chat", () => {
    const digestOnly: AssistantTurn[] = [
      {
        id: "d1",
        kind: "digest",
        status: "running",
        label: "Remember Collection.md, Light.md",
      },
    ];
    expect(isIdleSession({ turns: digestOnly })).toBe(false);
  });
});

describe("sessionHasDraft", () => {
  it("detects typed or attached drafts", () => {
    expect(sessionHasDraft({ draftInput: "  hello  " })).toBe(true);
    expect(
      sessionHasDraft({
        draftAttachments: [{ id: "1", name: "note.md" }],
      }),
    ).toBe(true);
    expect(sessionHasDraft({ draftInput: "   ", draftAttachments: [] })).toBe(
      false,
    );
  });
});

describe("shouldDiscardIdleSession", () => {
  it("discards unused New chats when leaving them", () => {
    expect(
      shouldDiscardIdleSession(
        { turns: blank },
        { isActive: false, isBusy: false },
      ),
    ).toBe(true);
    expect(
      shouldDiscardIdleSession({ turns: openerOnly }, { isActive: false }),
    ).toBe(true);
  });

  it("keeps chats with unsent typed draft when leaving", () => {
    expect(
      shouldDiscardIdleSession(
        { turns: blank, draftInput: "water hardness notes" },
        { isActive: false },
      ),
    ).toBe(false);
  });

  it("keeps the active New chat and any chat with a user turn", () => {
    expect(
      shouldDiscardIdleSession({ turns: blank }, { isActive: true }),
    ).toBe(false);
    expect(
      shouldDiscardIdleSession({ turns: withUser }, { isActive: false }),
    ).toBe(false);
  });

  it("does not discard a busy session", () => {
    expect(
      shouldDiscardIdleSession(
        { turns: blank },
        { isActive: false, isBusy: true },
      ),
    ).toBe(false);
  });
});
