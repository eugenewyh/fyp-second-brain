import { describe, expect, it } from "vitest";
import {
  filterUserSubfolders,
  folderNameFromPath,
  ideaBodyFromMarkdown,
  ideaMarkdownFromBody,
  parentDir,
  rewritePathPrefix,
} from "./project-edit";

describe("idea markdown", () => {
  it("round-trips a body through IDEA.md", () => {
    const md = ideaMarkdownFromBody("Track DLM vs JSON speed.");
    expect(md).toBe("# Idea\n\nTrack DLM vs JSON speed.\n");
    expect(ideaBodyFromMarkdown(md)).toBe("Track DLM vs JSON speed.");
  });

  it("strips the Idea heading and returns empty when the body is blank", () => {
    expect(ideaBodyFromMarkdown("# Idea\n\n")).toBe("");
    expect(ideaMarkdownFromBody("  ")).toBe("# Idea\n\n");
  });

  it("keeps markdown that has no Idea heading", () => {
    expect(ideaBodyFromMarkdown("Just a note.")).toBe("Just a note.");
  });
});

describe("rewritePathPrefix", () => {
  const from = "/vault/Alpha";
  const to = "/vault/Beta";

  it("rewrites the folder and descendant note paths", () => {
    expect(rewritePathPrefix(from, from, to)).toBe(to);
    expect(rewritePathPrefix(`${from}/`, from, to)).toBe(to);
    expect(rewritePathPrefix(`${from}/notes/a.md`, from, to)).toBe(`${to}/notes/a.md`);
  });

  it("does not rewrite a sibling whose name only shares a prefix", () => {
    expect(rewritePathPrefix("/vault/Alphabet/x.md", from, to)).toBe("/vault/Alphabet/x.md");
    expect(rewritePathPrefix("/vault/Other", from, to)).toBe("/vault/Other");
  });

  it("matches case-insensitively", () => {
    expect(rewritePathPrefix("/vault/alpha/notes/a.md", from, to)).toBe(`${to}/notes/a.md`);
  });
});

describe("filterUserSubfolders", () => {
  it("drops system dirs and hidden names", () => {
    expect(
      filterUserSubfolders(["Notes", "memory", "briefs", "watches", "research", ".git", "Sources"]),
    ).toEqual(["Notes", "Sources"]);
  });
});

describe("path parts", () => {
  it("reads the folder name and parent", () => {
    expect(folderNameFromPath("/vault/Skunkworks")).toBe("Skunkworks");
    expect(folderNameFromPath("/vault/Skunkworks/")).toBe("Skunkworks");
    expect(parentDir("/vault/Skunkworks")).toBe("/vault");
  });
});
