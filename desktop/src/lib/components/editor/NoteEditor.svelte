<script lang="ts">
  import { onMount, onDestroy, tick } from "svelte";
  import type { Editor } from "@tiptap/core";
  import { readNote, writeNote, loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import { splitFrontmatter } from "$lib/vault/markdown";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import {
    createEditorFromMarkdown,
    serializeOpenEditor,
    activateWikilink,
  } from "$lib/editor/note-editor-session";
  import { htmlBodyToMarkdown, markdownBodyToHtml } from "$lib/vault/markdown";
  import {
    loadEditorViewMode,
    loadSplitRatio,
    saveEditorViewMode,
    saveSplitRatio,
    type EditorViewMode,
  } from "$lib/workspace/editor-prefs";
  import PaneResizer from "$lib/components/workspace/PaneResizer.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";

  interface Props {
    path: string;
  }

  let { path }: Props = $props();
  let editorEl: HTMLDivElement | undefined = $state();
  let previewEl: HTMLDivElement | undefined = $state();
  let editor: Editor | null = null;
  let viewMode = $state<EditorViewMode>(loadEditorViewMode());
  let splitRatio = $state(loadSplitRatio());
  let previewHtml = $state("");
  let previewTimer: ReturnType<typeof setTimeout> | null = null;
  let loading = $state(true);
  let saving = $state(false);
  let vaultReady = $state(false);
  let error = $state("");
  let saveMessage = $state("");
  let frontmatter = $state("");
  let vaultFiles = $state<{ path: string; name: string }[]>([]);
  let lastVaultNonce = 0;

  async function refreshVaultFiles(): Promise<void> {
    vaultReady = false;
    if (!workspace.vaultRoot) {
      workspace.vaultRoot = await getVaultRoot();
    }
    const tree = await loadVaultTree(workspace.vaultRoot);
    vaultFiles = flattenVaultFiles(tree);
    vaultReady = true;
  }

  function handleWikilinkClick(event: MouseEvent) {
    if (!vaultReady) return;
    const el = (event.target as HTMLElement).closest("a[data-wikilink]");
    if (!el) return;
    const inEditor = editorEl?.contains(el);
    const inPreview = previewEl?.contains(el);
    if (!inEditor && !inPreview) return;
    event.preventDefault();
    const target = el.getAttribute("data-wikilink");
    if (!target) return;
    const resolved = activateWikilink(target, vaultFiles);
    if (resolved) {
      tabs.openNoteTab(resolved);
      workspace.setActiveNote(resolved);
    }
  }

  function schedulePreviewUpdate() {
    if (!editor) return;
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(() => {
      const body = htmlBodyToMarkdown(editor!.getHTML());
      previewHtml = markdownBodyToHtml(body);
    }, 150);
  }

  function setViewMode(mode: EditorViewMode) {
    viewMode = mode;
    saveEditorViewMode(mode);
    schedulePreviewUpdate();
  }

  function onSplitResize(delta: number) {
    const wrap = editorEl?.parentElement?.parentElement;
    if (!wrap) return;
    const total = wrap.clientWidth || 1;
    splitRatio = Math.min(0.75, Math.max(0.25, splitRatio + delta / total));
    saveSplitRatio(splitRatio);
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

      editor = createEditorFromMarkdown(parts.body, editorEl, {
        editorProps: {
          attributes: { class: "tiptap-surface" },
        },
        onUpdate: () => schedulePreviewUpdate(),
        onSelectionUpdate: ({ editor: ed }) => {
          const { from, to } = ed.state.selection;
          if (from !== to) {
            workspace.selectedText = ed.state.doc.textBetween(from, to, " ");
          }
        },
      });
      previewHtml = markdownBodyToHtml(parts.body);
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
      const content = serializeOpenEditor(editor, frontmatter);
      await writeNote(path, content);
      saveMessage = "Saved";
      workspace.requestVaultRefresh();
      await refreshVaultFiles();
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
      void refreshVaultFiles();
    }
  });

  onMount(() => {
    initEditor();
    editorEl?.addEventListener("click", handleWikilinkClick);
    previewEl?.addEventListener("click", handleWikilinkClick);
  });

  onDestroy(() => {
    if (previewTimer) clearTimeout(previewTimer);
    editorEl?.removeEventListener("click", handleWikilinkClick);
    previewEl?.removeEventListener("click", handleWikilinkClick);
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
    <div class="toolbar-actions">
      <div class="view-toggle" role="group" aria-label="Editor view mode">
        <button class:active={viewMode === "edit"} onclick={() => setViewMode("edit")}>Edit</button>
        <button class:active={viewMode === "split"} onclick={() => setViewMode("split")}>Split</button>
        <button class:active={viewMode === "preview"} onclick={() => setViewMode("preview")}>Preview</button>
      </div>
      <button class="btn-primary" onclick={saveNote} disabled={saving || loading || !!error}>
        {saving ? "Saving…" : "Save"}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading note…</div>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div
    class="editor-layout"
    class:split={viewMode === "split"}
    class:preview-only={viewMode === "preview"}
    class:hidden={loading || !!error}
  >
    {#if viewMode !== "preview"}
      <div class="editor-wrap" style={viewMode === "split" ? `flex: ${splitRatio}` : ""} bind:this={editorEl}></div>
    {/if}
    {#if viewMode === "split"}
      <PaneResizer onResize={onSplitResize} />
    {/if}
    {#if viewMode !== "edit"}
      <div
        class="preview-wrap"
        style={viewMode === "split" ? `flex: ${1 - splitRatio}` : ""}
        bind:this={previewEl}
      >
        {@html previewHtml}
      </div>
    {/if}
  </div>

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

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .view-toggle {
    display: flex;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .view-toggle button {
    font-size: 0.7rem;
    padding: 0.35rem 0.55rem;
    background: var(--surface);
    color: var(--text-muted);
    border: none;
    border-radius: 0;
  }

  .view-toggle button.active {
    background: var(--accent);
    color: white;
  }

  .editor-layout {
    display: flex;
    min-height: 50vh;
    max-height: 70vh;
    gap: 0;
  }

  .editor-layout.hidden {
    display: none;
  }

  .editor-layout.preview-only .preview-wrap {
    flex: 1;
  }

  .path-hint {
    font-size: 0.75rem;
    word-break: break-all;
    color: var(--text-muted);
  }

  .editor-wrap,
  .preview-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow-y: auto;
    padding: 1rem 1.25rem;
    min-height: 50vh;
  }

  .editor-wrap {
    flex: 1;
  }

  .preview-wrap {
    flex: 1;
    line-height: 1.6;
  }

  .preview-wrap :global(a.wikilink) {
    color: var(--accent);
    text-decoration: underline;
    cursor: pointer;
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