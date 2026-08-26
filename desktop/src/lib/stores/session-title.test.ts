import { describe, expect, it } from "vitest";
import {
  DEFAULT_SESSION_TITLE,
  canApplyLlmSessionTitle,
  isPlaceholderSessionTitle,
  isTruncatedAutoTitle,
  normalizeLlmSessionTitle,
  phraseTitleFromText,
  titleFromSessionTurns,
  truncateSessionTitle,
} from "./session-title";

describe("session-title", () => {
  it("treats default labels as placeholders", () => {
    expect(isPlaceholderSessionTitle("New chat")).toBe(true);
    expect(isPlaceholderSessionTitle("New Chat")).toBe(true);
    expect(isPlaceholderSessionTitle("New research")).toBe(true);
    expect(isPlaceholderSessionTitle("What is diffusion?")).toBe(false);
  });

  it("treats workspace folder names as placeholders", () => {
    expect(isPlaceholderSessionTitle("Coffee", "Coffee")).toBe(true);
    expect(isPlaceholderSessionTitle("Coffee", "TEST")).toBe(false);
  });

  it("truncates long titles", () => {
    const long = "a".repeat(60);
    expect(truncateSessionTitle(long).length).toBe(36);
    expect(truncateSessionTitle(long).endsWith("…")).toBe(true);
  });

  it("detects truncated auto titles", () => {
    expect(isTruncatedAutoTitle("What's my weekday mornin…")).toBe(true);
    expect(isTruncatedAutoTitle("Morning Watch")).toBe(false);
  });

  it("builds short Cursor-style phrases", () => {
    expect(phraseTitleFromText("What's my weekday morning watch schedule?")).toBe(
      "Weekday Morning Watch Schedule",
    );
    expect(
      phraseTitleFromText(
        "According to my notes, what do I care about in diffusion language models?",
      ),
    ).toBe("Care About in Diffusion Language");
    expect(phraseTitleFromText("Explain constrained decoding for DLMs")).toBe(
      "Constrained Decoding for DLMs",
    );
    expect(phraseTitleFromText("hi")).toBeNull();
  });

  it("prefers the first user message (Cursor-style)", () => {
    expect(
      titleFromSessionTurns([
        { kind: "user", content: "Explain constrained decoding for DLMs" },
      ]),
    ).toBe("Constrained Decoding for DLMs");
    expect(
      titleFromSessionTurns([
        { kind: "user", content: "What do I care about for espresso?" },
        { kind: "research", query: "Latest papers on diffusion LLMs" },
      ]),
    ).toBe("Care About for Espresso");
    expect(
      titleFromSessionTurns([
        { kind: "research", query: "Latest papers on diffusion LLMs" },
      ]),
    ).toBe("Latest Papers on Diffusion LLMs");
  });

  it("exports New Chat as the default label", () => {
    expect(DEFAULT_SESSION_TITLE).toBe("New Chat");
  });

  it("normalizes LLM titles", () => {
    expect(normalizeLlmSessionTitle('"Espresso Grinders Under $500"')).toBe(
      "Espresso Grinders Under $500",
    );
    expect(normalizeLlmSessionTitle("Title: Single Dose Grinders")).toBe(
      "Single Dose Grinders",
    );
    expect(normalizeLlmSessionTitle("New Chat")).toBeNull();
  });

  it("allows LLM overwrite for weak auto titles", () => {
    expect(canApplyLlmSessionTitle("New Chat")).toBe(true);
    expect(canApplyLlmSessionTitle("I Already Know From my…")).toBe(true);
    expect(
      canApplyLlmSessionTitle("I Already Know From my", null, "I Already Know From my"),
    ).toBe(true);
    expect(canApplyLlmSessionTitle("My Custom Name")).toBe(false);
  });
});
