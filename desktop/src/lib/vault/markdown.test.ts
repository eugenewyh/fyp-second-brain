import { describe, expect, it } from "vitest";
import { generateJSON } from "@tiptap/html";
import StarterKit from "@tiptap/starter-kit";
import { WikiLink } from "$lib/editor/wikilink-extension";
import { markdownBodyToHtml, htmlBodyToMarkdown } from "./markdown";

const extensions = [StarterKit, WikiLink];

describe("markdown roundtrip", () => {
  it("preserves bold, italic, inline code, and headings", () => {
    const source = [
      "## Section",
      "",
      "This is **bold** and *italic* with `inline code`.",
      "",
      "- first item",
      "- second item",
    ].join("\n");

    const roundtrip = htmlBodyToMarkdown(markdownBodyToHtml(source));
    expect(roundtrip).toContain("## Section");
    expect(roundtrip).toContain("**bold**");
    expect(roundtrip).toContain("*italic*");
    expect(roundtrip).toContain("`inline code`");
    expect(roundtrip).toMatch(/-\s+first item/);
  });

  it("preserves wikilinks through html roundtrip", () => {
    const source = "See [[Servlets]] and [[Java|JDK notes]] here.";
    const roundtrip = htmlBodyToMarkdown(markdownBodyToHtml(source));
    expect(roundtrip).toContain("[[Servlets]]");
    expect(roundtrip).toContain("[[Java|JDK notes]]");
  });

  it("loads wikilinks into TipTap JSON with target attrs", () => {
    const html = markdownBodyToHtml("Link [[Target|alias]] text.");
    const doc = generateJSON(html, extensions);

    const marks: { type: string; attrs?: Record<string, unknown> }[] = [];
    const walk = (node: { type?: string; marks?: typeof marks; content?: unknown[] }) => {
      if (node.marks) marks.push(...node.marks);
      if (node.content) node.content.forEach((c) => walk(c as typeof node));
    };
    walk(doc);

    const wiki = marks.find((m) => m.type === "wikiLink");
    expect(wiki?.attrs?.target).toBe("Target");
    expect(wiki?.attrs?.alias).toBe("alias");
  });

  it("serializes TipTap wikilink HTML back to markdown syntax", () => {
    const html =
      '<p>Go to <a data-wikilink="Note" class="wikilink" href="#">Note</a>.</p>';
    const md = htmlBodyToMarkdown(html);
    expect(md).toContain("[[Note]]");
  });
});