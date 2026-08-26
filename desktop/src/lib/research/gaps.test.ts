import { describe, expect, it } from "vitest";
import { extractOpenQuestions } from "./gaps";

describe("extractOpenQuestions", () => {
  it("reads Identified Gaps", () => {
    const qs = extractOpenQuestions(
      "## Identified Gaps\n- Missing evaluation of long-horizon goals in student workflows\n",
    );
    expect(qs.some((q) => /missing evaluation/i.test(q))).toBe(true);
  });

  it("reads What's missing", () => {
    const qs = extractOpenQuestions(
      "## What's missing\n- Unclear how memory compounds across sessions over a semester\n",
    );
    expect(qs.some((q) => /memory compounds/i.test(q))).toBe(true);
  });
});
