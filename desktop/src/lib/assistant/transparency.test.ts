import { describe, expect, it } from "vitest";
import {
  formatDigestSummary,
  formatRetrievalSummary,
  formatRevisionSummary,
  getLatestResearchResult,
  retrievalOriginChips,
} from "./transparency";

describe("formatRetrievalSummary", () => {
  it("formats mixed source counts with personal-first wording", () => {
    expect(formatRetrievalSummary({ personal: 3, web: 5, arxiv: 2 })).toBe(
      "Based on 3 notes from your library, 5 web sources, and 2 arXiv papers",
    );
  });

  it("handles two origins with and", () => {
    expect(formatRetrievalSummary({ personal: 4, web: 2 })).toBe(
      "Based on 4 notes from your library and 2 web sources",
    );
  });

  it("handles empty stats", () => {
    expect(formatRetrievalSummary({})).toBe(
      "No sources from your notes or the web",
    );
  });
});

describe("formatRevisionSummary", () => {
  it("describes zero revisions", () => {
    expect(formatRevisionSummary(0)).toBe(
      "Verifier reviewed the analysis (no revision needed)",
    );
  });

  it("describes multiple revisions", () => {
    expect(formatRevisionSummary(2)).toBe(
      "Verifier requested 2 revisions (architectural self-critique)",
    );
  });
});

describe("retrievalOriginChips", () => {
  it("returns chips for present origins", () => {
    const chips = retrievalOriginChips({ personal: 2, web: 1 });
    expect(chips.map((c) => c.key)).toEqual(["personal", "web"]);
  });
});

describe("formatDigestSummary", () => {
  it("summarizes remember write-back", () => {
    expect(
      formatDigestSummary({ created: 2, revised: 1, dropped: 3, idempotent: true }),
    ).toBe("Already in memory · 2 claims remembered · 1 updated · 3 skipped");
  });
});

describe("getLatestResearchResult", () => {
  it("returns the most recent research result", () => {
    const result = getLatestResearchResult([
      { kind: "user" },
      { kind: "research", result: { query: "a" } as never },
      { kind: "quick" },
      { kind: "research", result: { query: "b" } as never },
    ]);
    expect(result?.query).toBe("b");
  });
});
