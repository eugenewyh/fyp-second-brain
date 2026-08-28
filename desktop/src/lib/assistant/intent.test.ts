import { describe, expect, it } from "vitest";
import {
  classifyIntent,
  hasLearnIntent,
  hasResearchIntent,
  hasLookupVerbs,
  isNoteDump,
  leftoverQuestionAfterTeach,
  shouldAutoResearch,
} from "./intent";

const DUMP = [
  "Retrieval-augmented generation still fabricates citations when the corpus is thin.",
  "",
  "Long-context models can beat RAG on short document sets in several 2024 studies.",
  "",
  "Students should verify every citation against the original PDF before trusting a report.",
  "",
  "Claim revision matters more than fluency when the library already contains a conflicting note.",
].join("\n");

describe("classifyIntent", () => {
  it("treats attachments as teach", () => {
    expect(classifyIntent({ text: "What is RAG?", hasAttachments: true })).toBe("teach");
  });

  it("treats a long note-like paste as teach", () => {
    expect(classifyIntent({ text: DUMP })).toBe("teach");
  });

  it("does not teach a short accidental paste", () => {
    expect(classifyIntent({ text: "RAG still fabricates citations sometimes." })).toBe(
      "explain",
    );
  });

  it("explains ordinary questions", () => {
    expect(classifyIntent({ text: "What do I already believe about RAG?" })).toBe(
      "explain",
    );
  });

  it("explains notes-grounded questions instead of looking up", () => {
    expect(
      classifyIntent({
        text: "According to my notes, what do I care about in diffusion language models besides raw generation speed?",
      }),
    ).toBe("explain");
  });

  it("looks up when asked for latest / arxiv / web", () => {
    expect(classifyIntent({ text: "What's the latest evidence on RAG vs long context?" })).toBe(
      "lookup",
    );
    expect(classifyIntent({ text: "Find papers on citation hallucination" })).toBe("lookup");
    expect(classifyIntent({ text: "Look up arxiv papers on self-critique" })).toBe("lookup");
    expect(classifyIntent({ text: "What's new in hybrid retrieval?" })).toBe("lookup");
    expect(hasLookupVerbs("search the web for hybrid retrieval")).toBe(true);
  });

  it("treats synthesise + cite notes as lookup (research)", () => {
    expect(
      classifyIntent({
        text: "Synthesise my stance on home espresso: grind vs dose. Cite my notes.",
      }),
    ).toBe("lookup");
  });

  it("treats Research mission phrasing as lookup", () => {
    expect(
      classifyIntent({
        text: "Research how specialty coffee roasting affects flavor — compare light vs dark roast",
      }),
    ).toBe("lookup");
    expect(hasResearchIntent("Research indoor plant care")).toBe(true);
    expect(
      shouldAutoResearch(
        "Research how specialty coffee roasting affects flavor — compare light vs dark roast",
      ),
    ).toBe(true);
  });

  it("explains teach-me-about as learning from notes, not teach", () => {
    expect(hasLearnIntent("teach everything about lec10")).toBe(true);
    expect(classifyIntent({ text: "teach everything about lec10" })).toBe("explain");
    expect(classifyIntent({ text: "Teach me about session beans" })).toBe("explain");
  });
});

describe("isNoteDump", () => {
  it("requires length or multiple paragraphs and no question", () => {
    expect(isNoteDump("Hello")).toBe(false);
    expect(isNoteDump("What is RAG?")).toBe(false);
    expect(isNoteDump(DUMP)).toBe(true);
  });
});

describe("leftoverQuestionAfterTeach", () => {
  it("keeps a question after filing files", () => {
    expect(leftoverQuestionAfterTeach("What is in this PDF?")).toBe(
      "What is in this PDF?",
    );
  });

  it("returns null for a pure dump", () => {
    expect(leftoverQuestionAfterTeach(DUMP)).toBeNull();
  });
});
