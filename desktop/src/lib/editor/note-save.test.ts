import { describe, expect, it } from "vitest";
import { serializeEditorHtmlToNote } from "./note-save";

describe("note-save (editor.getHTML path)", () => {
  it("serializes TipTap getHTML output the same way NoteEditor.saveNote does", () => {
    const editorHtml =
      '<p>See <a data-wikilink="Target" class="wikilink" href="#">alias</a> and <strong>bold</strong></p>';
    const saved = serializeEditorHtmlToNote("---\ntitle: test\n---\n", editorHtml);

    expect(saved.startsWith("---\ntitle: test\n---\n")).toBe(true);
    expect(saved).toContain("[[Target|alias]]");
    expect(saved).toContain("**bold**");
  });
});