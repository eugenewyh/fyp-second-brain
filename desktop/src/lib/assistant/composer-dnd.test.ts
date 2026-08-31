import { describe, expect, it } from "vitest";
import { filterAttachablePaths, isAttachablePath } from "./composer-dnd";

describe("composer-dnd path filters", () => {
  it("accepts md / txt / pdf / docx", () => {
    expect(isAttachablePath("/Users/me/notes/water-and-dial-in.md")).toBe(true);
    expect(isAttachablePath("C:\\vault\\note.TXT")).toBe(true);
    expect(isAttachablePath("/tmp/paper.pdf")).toBe(true);
    expect(isAttachablePath("/tmp/essay.docx")).toBe(true);
  });

  it("rejects other extensions", () => {
    expect(isAttachablePath("/tmp/photo.png")).toBe(false);
    expect(isAttachablePath("/tmp/archive.zip")).toBe(false);
  });

  it("filters a mixed path list", () => {
    expect(
      filterAttachablePaths([
        "/a/note.md",
        "/a/skip.jpg",
        "/a/readme.txt",
        "/a/doc.pdf",
        "/a/essay.docx",
      ]),
    ).toEqual(["/a/note.md", "/a/readme.txt", "/a/doc.pdf", "/a/essay.docx"]);
  });
});
