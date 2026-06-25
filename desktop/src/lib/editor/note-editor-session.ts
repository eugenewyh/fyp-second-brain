import { Editor, type EditorOptions, type Extensions } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { WikiLink } from "$lib/editor/wikilink-extension";
import { markdownBodyToHtml, htmlBodyToMarkdown, joinFrontmatter } from "$lib/vault/markdown";
import { resolveWikilinkTarget } from "$lib/vault/wikilinks";
import type { VaultFileRef } from "$lib/vault/flatten";

export const NOTE_EDITOR_EXTENSIONS: Extensions = [StarterKit, WikiLink];

/** Create a TipTap editor from markdown body (same extensions + load path as NoteEditor). */
export function createEditorFromMarkdown(
  body: string,
  element?: HTMLElement,
  options?: Partial<EditorOptions>,
): Editor {
  const el = element ?? document.createElement("div");
  const html = markdownBodyToHtml(body);
  return new Editor({
    element: el,
    extensions: NOTE_EDITOR_EXTENSIONS,
    content: html || "<p></p>",
    ...options,
  });
}

/** Serialize open editor HTML + frontmatter to a note file string (NoteEditor.saveNote path). */
export function serializeOpenEditor(editor: Editor, frontmatter: string): string {
  const body = htmlBodyToMarkdown(editor.getHTML());
  return joinFrontmatter({ frontmatter, body });
}

/** Resolve clicked wikilink against vault file index (NoteEditor click handler path). */
export function activateWikilink(dataWikilink: string, vaultFiles: VaultFileRef[]): string | null {
  return resolveWikilinkTarget(dataWikilink, vaultFiles);
}