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
  import SegmentedControl from "$lib/ui/SegmentedControl.svelte";
  import Button from "$lib/ui/Button.svelte";
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

<section class="note-editor">
  <div class="toolbar">
    <span class="title">{path.split("/").pop()}</span>
    <div class="toolbar-actions">
      <SegmentedControl
        options={[
          { value: "edit", label: "Edit" },
          { value: "split", label: "Split" },
          { value: "preview", label: "Preview" },
        ]}
        bind:value={viewMode}
        onchange={(v) => setViewMode(v as EditorViewMode)}
      />
      <Button variant="primary" onclick={saveNote} disabled={saving || loading || !!error}>
        {saving ? "Saving…" : "Save"}
      </Button>
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
</section>

<style>
  .note-editor {
    display: flex;
    flex-direction: column;
    height: 100%;
    flex: 1;
    min-height: 0;
  }

  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .title {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .editor-layout {
    display: flex;
    flex: 1;
    min-height: 0;
    gap: 0;
  }

  .editor-layout.hidden {
    display: none;
  }

  .editor-wrap,
  .preview-wrap {
    background: var(--bg-elevated);
    overflow-y: auto;
    padding: 1rem 1.25rem;
    flex: 1;
    min-height: 0;
  }

  .preview-wrap {
    line-height: 1.6;
    font-size: 0.875rem;
  }

  .preview-wrap :global(a.wikilink) {
    color: var(--accent);
    text-decoration: none;
    cursor: pointer;
  }

  .preview-wrap :global(a.wikilink:hover) {
    text-decoration: underline;
  }

  .save-msg {
    padding: 0.35rem 0.75rem;
    font-size: 0.7rem;
    color: var(--success);
    border-top: 1px solid var(--border-subtle);
  }

  .loading {
    padding: 1rem;
    font-size: 0.75rem;
    color: var(--text-faint);
  }

  .error {
    padding: 0.75rem;
    font-size: 0.75rem;
    color: var(--error);
  }
</style>