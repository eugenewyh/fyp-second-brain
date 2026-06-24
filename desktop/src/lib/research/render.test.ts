import { describe, expect, it } from "vitest";
import { renderReport } from "./render";

describe("renderReport", () => {
  it("converts markdown headings to h2 tags", () => {
    const html = renderReport("## Executive Summary\n\nFindings here.");
    expect(html).toContain("<h2>Executive Summary</h2>");
  });

  it("converts bullet lines to li tags", () => {
    const html = renderReport("- First point\n- Second point");
    expect(html).toContain("<li>First point</li>");
    expect(html).toContain("<li>Second point</li>");
  });
});