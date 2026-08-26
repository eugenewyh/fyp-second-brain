import { describe, expect, it } from "vitest";
import {
  displayReportTitle,
  extractKeyFindings,
  parseReportSections,
  parseSourcesSection,
  renderReport,
  renderSectionBody,
} from "./render";

const SAMPLE = `## Executive Summary
Servlets handle HTTP.

## Key Findings
- Finding one about architecture
- Finding two about lifecycle

## Sources
[1] Personal — Lec03.pdf, p.12
[2] Web — Tutorial (https://example.com/servlets)
`;

describe("render report (Elicit-style)", () => {
  it("parses sections", () => {
    const secs = parseReportSections(SAMPLE);
    expect(secs.map((s) => s.title)).toContain("Key Findings");
    expect(secs.length).toBeGreaterThanOrEqual(3);
  });

  it("extracts findings bullets", () => {
    const f = extractKeyFindings(SAMPLE);
    expect(f.length).toBe(2);
    expect(f[0]).toMatch(/architecture/i);
  });

  it("parses sources table rows", () => {
    const rows = parseSourcesSection(SAMPLE);
    expect(rows).toHaveLength(2);
    expect(rows[0].origin).toBe("personal");
    expect(rows[1].origin).toBe("web");
  });

  it("parses Notion source rows", () => {
    const md = `## Sources
[1] Notion — Meeting notes (https://www.notion.so/aaaaaaaa)
`;
    const rows = parseSourcesSection(md);
    expect(rows).toHaveLength(1);
    expect(rows[0].origin).toBe("notion");
  });

  it("renderReport produces headings", () => {
    const html = renderReport(SAMPLE);
    expect(html).toContain("<h2");
    expect(html).toContain("Key Findings");
  });

    it("attaches hover titles to citations", () => {
    const html = renderSectionBody("Claim [1] holds.", new Map([[1, "Personal — Lec03.pdf"]]));
    expect(html).toContain('data-cite="1"');
    expect(html).toContain('title="Personal — Lec03.pdf"');
  });

  it("maps legacy headings to everyday titles", () => {
    expect(displayReportTitle("Executive Summary")).toBe("In short");
    expect(displayReportTitle("Key Findings")).toBe("What we found");
    expect(displayReportTitle("Detailed Analysis")).toBe("The details");
    expect(displayReportTitle("Identified Gaps")).toBe("What's missing");
    expect(displayReportTitle("In short")).toBe("In short");
  });

  it("extracts findings from plain headings", () => {
    const md = `## In short
Servlets handle HTTP.

## What we found
- Finding one about architecture
- Finding two about lifecycle
`;
    expect(extractKeyFindings(md)).toHaveLength(2);
    expect(parseReportSections(md).map((s) => s.title)).toContain("What we found");
  });
});
