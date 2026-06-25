import { describe, expect, it, afterEach } from "vitest";
import {
  NOTE_EDITOR_EXTENSIONS,
  createEditorFromMarkdown,
  serializeOpenEditor,
  activateWikilink,
} from "./note-editor-session";

const staleVault = [{ path: "/vault/old.md", name: "old.md" }];
const freshVault = [
  ...staleVault,
  { path: "/vault/research/new-note.md", name: "new-note.md" },
];

let editor: ReturnType<typeof createEditorFromMarkdown> | null = null;

afterEach(() => {
  editor?.destroy();
  editor = null;
});

describe("note-editor-session (real TipTap Editor)", () => {
  it("uses NOTE_EDITOR_EXTENSIONS including WikiLink", () => {
    expect(NOTE_EDITOR_EXTENSIONS).toHaveLength(2);
    expect(NOTE_EDITOR_EXTENSIONS.map((e) => e.name)).toContain("wikiLink");
  });

  it("createEditorFromMarkdown preserves data-wikilink in getHTML", () => {
    const body = "See [[Target|alias]] and **bold** text.";
    editor = createEditorFromMarkdown(body);
    const html = editor.getHTML();
    expect(html).toContain('data-wikilink="Target"');
    expect(html).toContain("<strong>bold</strong>");
  });

  it("serializeOpenEditor round-trips wikilinks and bold via getHTML", () => {
    editor = createEditorFromMarkdown("Link [[Target|alias]] and **bold**.");
    const saved = serializeOpenEditor(editor, "---\ntitle: t\n---\n");
    expect(saved).toContain("[[Target|alias]]");
    expect(saved).toContain("**bold**");
    expect(saved.startsWith("---\ntitle: t\n---\n")).toBe(true);
  });

  it("activateWikilink fails on stale vault index then succeeds after refresh", () => {
    expect(activateWikilink("new-note", staleVault)).toBeNull();
    expect(activateWikilink("new-note", freshVault)).toBe("/vault/research/new-note.md");
  });
});