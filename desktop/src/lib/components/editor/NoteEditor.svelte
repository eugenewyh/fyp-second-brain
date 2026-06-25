<script lang="ts">
  import { onMount, onDestroy, tick } from "svelte";
  import { Editor } from "@tiptap/core";
  import StarterKit from "@tiptap/starter-kit";
  import { readNote, writeNote, loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import { splitFrontmatter, markdownBodyToHtml } from "$lib/vault/markdown";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import { serializeEditorHtmlToNote } from "$lib/editor/note-save";
  import { activateWikilinkTarget } from "$lib/editor/wikilink-click";
  import { WikiLink } from "$lib/editor/wikilink-extension";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";

  interface Props {
    path: string;
  }

  let { path }: Props = $props();
  let editorEl: HTMLDivElement | undefined = $state();
  let editor: Editor | null = null;
  let loading = $state(true);
  let saving = $state(false);
  let error = $state("");
  let saveMessage = $state("");
  let frontmatter = $state("");
  let vaultFiles = $state<{ path: string; name: string }[]>([]);
  let lastVaultNonce = 0;

  async function refreshVaultFiles() {
    if (!workspace.vaultRoot) {
      workspace.vaultRoot = await getVaultRoot();
    }
    const tree = await loadVaultTree(workspace.vaultRoot);
    vaultFiles = flattenVaultFiles(tree);
  }

  function handleWikilinkClick(event: MouseEvent) {
    const el = (event.target as HTMLElement).closest("a[data-wikilink]");
    if (!el || !editorEl?.contains(el)) return;
    event.preventDefault();
    const target = el.getAttribute("data-wikilink");
    if (!target) return;
    const resolved = activateWikilinkTarget(target, vaultFiles);
    if (resolved) {
      tabs.openNoteTab(resolved);
      workspace.setActiveNote(resolved);
    }
  }

  async function initEditor() {
    loading = true;
    error = "";
    saveMessage = "";
    workspace.setActiveNote(path);
    editor?.destroy();
    editor = null;

    try {
      await tick();
      if (!editorEl) throw new Error("Editor surface not ready");

      await refreshVaultFiles();

      const raw = await readNote(path);
      const parts = splitFrontmatter(raw);
      frontmatter = parts.frontmatter;
      const html = markdownBodyToHtml(parts.body);

      editor = new Editor({
        element: editorEl,
        extensions: [StarterKit, WikiLink],
        content: html || "<p></p>",
        editorProps: {
          attributes: { class: "tiptap-surface" },
        },
        onSelectionUpdate: ({ editor: ed }) => {
          const { from, to } = ed.state.selection;
          if (from !== to) {
            workspace.selectedText = ed.state.doc.textBetween(from, to, " ");
          }
        },
      });
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load note";
    } finally {
      loading = false;
    }
  }

  async function saveNote() {
    if (!editor) return;
    saving = true;
    saveMessage = "";
    try {
      const content = serializeEditorHtmlToNote(frontmatter, editor.getHTML());
      await writeNote(path, content);
      saveMessage = "Saved";
      workspace.requestVaultRefresh();
    } catch (e) {
      saveMessage = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    const nonce = workspace.vaultRefreshNonce;
    if (nonce > 0 && nonce !== lastVaultNonce && !loading) {
      lastVaultNonce = nonce;
      refreshVaultFiles();
    }
  });

  onMount(() => {
    initEditor();
    editorEl?.addEventListener("click", handleWikilinkClick);
  });

  onDestroy(() => {
    editorEl?.removeEventListener("click", handleWikilinkClick);
    editor?.destroy();
    editor = null;
  });
</script>

<section class="panel">
  <div class="toolbar">
    <div>
      <h2>{path.split("/").pop()}</h2>
      <p class="hint path-hint">{path}</p>
    </div>
    <button class="btn-primary" onclick={saveNote} disabled={saving || loading || !!error}>
      {saving ? "Saving…" : "Save"}
    </button>
  </div>

  {#if loading}
    <div class="loading">Loading note…</div>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div class="editor-wrap" class:hidden={loading || !!error} bind:this={editorEl}></div>

  {#if saveMessage}
    <p class="save-msg">{saveMessage}</p>
  {/if}
  {#if !loading && !error}
    <p class="wikilink-hint">
      Type <code>[[Note Name]]</code> or <code>[[Target|alias]]</code> for wikilinks.
    </p>
  {/if}
</section>

<style>
  .panel h2 {
    font-size: 1.2rem;
    margin-bottom: 0.2rem;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
    gap: 1rem;
  }

  .path-hint {
    font-size: 0.75rem;
    word-break: break-all;
    color: var(--text-muted);
  }

  .editor-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    min-height: 50vh;
    max-height: 70vh;
    overflow-y: auto;
    padding: 1rem 1.25rem;
  }

  .editor-wrap.hidden {
    display: none;
  }

  :global(.tiptap-surface) {
    outline: none;
    line-height: 1.6;
    min-height: 45vh;
  }

  :global(.tiptap-surface h1) {
    font-size: 1.35rem;
    margin: 0.75rem 0 0.5rem;
  }

  :global(.tiptap-surface h2) {
    font-size: 1.1rem;
    color: var(--accent);
    margin: 0.75rem 0 0.4rem;
  }

  :global(.tiptap-surface ul) {
    padding-left: 1.2rem;
    margin: 0.5rem 0;
  }

  :global(.tiptap-surface a.wikilink) {
    color: var(--accent);
    text-decoration: underline;
    cursor: pointer;
  }

  .save-msg {
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--success);
  }

  .wikilink-hint {
    margin-top: 0.5rem;
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .wikilink-hint code {
    color: var(--accent);
  }

  .loading {
    color: var(--warning);
    padding: 1rem;
    background: var(--surface);
    border-radius: var(--radius);
  }

  .error {
    color: var(--error);
  }
</style>