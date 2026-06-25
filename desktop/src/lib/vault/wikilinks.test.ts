import { describe, expect, it } from "vitest";
import {
  parseWikilinks,
  resolveWikilinkTarget,
  wikilinksToHtml,
  wikilinksInMarkdownToSyntax,
} from "./wikilinks";

describe("wikilinks", () => {
  it("parses plain and alias wikilinks", () => {
    const text = "See [[Servlets]] and [[Java|JDK notes]] for more.";
    const links = parseWikilinks(text);
    expect(links).toHaveLength(2);
    expect(links[0]).toMatchObject({ target: "Servlets", alias: "Servlets" });
    expect(links[1]).toMatchObject({ target: "Java", alias: "JDK notes" });
  });

  it("renders wikilinks as clickable HTML anchors", () => {
    const html = wikilinksToHtml("Link [[Target|label]] here");
    expect(html).toContain('data-wikilink="Target"');
    expect(html).toContain("label");
  });

  it("round-trips wikilinks through HTML back to markdown syntax", () => {
    const html = '<a data-wikilink="Note" class="wikilink">Note</a>';
    expect(wikilinksInMarkdownToSyntax(html)).toBe("[[Note]]");
    const aliased =
      '<a data-wikilink="Target" class="wikilink">alias</a>';
    expect(wikilinksInMarkdownToSyntax(aliased)).toBe("[[Target|alias]]");
  });

  it("resolves target by markdown filename", () => {
    const files = [
      { path: "/vault/research/servlets.md", name: "servlets.md" },
      { path: "/vault/java-overview.md", name: "java-overview.md" },
    ];
    expect(resolveWikilinkTarget("servlets", files)).toBe("/vault/research/servlets.md");
    expect(resolveWikilinkTarget("missing", files)).toBeNull();
  });
});