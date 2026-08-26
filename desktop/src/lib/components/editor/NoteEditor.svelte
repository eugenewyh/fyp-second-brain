<script lang="ts">
  import { onDestroy, tick } from "svelte";
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
  import { parsePeekMeta, stripLiftedPeekMeta } from "$lib/vault/graph-peek";
  import PaneResizer from "$lib/components/workspace/PaneResizer.svelte";
  import SegmentedControl from "$lib/ui/SegmentedControl.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";

  interface Props {
    path: string;
    compact?: boolean;
  }

  let { path, compact = false }: Props = $props();
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
  let loadedPath = "";

  function formatError(e: unknown): string {
    if (e instanceof Error) return e.message;
    if (typeof e === "string") return e;
    if (e && typeof e === "object" && "message" in e) {
      return String((e as { message: unknown }).message);
    }
    return "Failed to load note";
  }

  async function refreshVaultFiles(): Promise<void> {
    vaultReady = false;
    if (!workspace.vaultRoot) {
      workspace.vaultRoot = await getVaultRoot();
    }
    const tree = await loadVaultTree(workspace.vaultRoot);
    vaultFiles = flattenVaultFiles(tree);
    vaultReady = true;
  }

  function handlePreviewClick(event: MouseEvent) {
    const el = event.target as HTMLElement | null;
    const wiki = el?.closest?.("a[data-wikilink]");
    if (wiki) {
      if (!vaultReady) return;
      const inEditor = editorEl?.contains(wiki);
      const inPreview = previewEl?.contains(wiki);
      if (!inEditor && !inPreview) return;
      event.preventDefault();
      const target = wiki.getAttribute("data-wikilink");
      if (!target) return;
      const resolved = activateWikilink(target, vaultFiles);
      if (resolved) {
        tabs.openNoteTab(resolved);
        workspace.setActiveNote(resolved);
      }
      return;
    }
    const hrefEl = el?.closest?.("a[href]");
    if (!hrefEl) return;
    const href = hrefEl.getAttribute("href");
    if (!href || !/^https?:\/\//i.test(href)) return;
    const inPreview = previewEl?.contains(hrefEl);
    if (!inPreview) return;
    event.preventDefault();
    window.open(href, "_blank", "noopener");
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
    if (mode === "preview") {
      editor?.destroy();
      editor = null;
    } else if (!editor && !loading && !error) {
      void initEditorForPath(path);
    } else {
      schedulePreviewUpdate();
    }
  }

  function onSplitResize(delta: number) {
    const wrap = editorEl?.parentElement?.parentElement;
    if (!wrap) return;
    const total = wrap.clientWidth || 1;
    splitRatio = Math.min(0.75, Math.max(0.25, splitRatio + delta / total));
    saveSplitRatio(splitRatio);
  }

  async function initEditorForPath(notePath: string) {
    loading = true;
    error = "";
    saveMessage = "";
    workspace.setActiveNote(notePath);
    editor?.destroy();
    editor = null;
    previewHtml = "";

    try {
      await refreshVaultFiles();

      const raw = await readNote(notePath);
      const parts = splitFrontmatter(raw);
      frontmatter = parts.frontmatter;
      let previewBody = parts.body;
      if (compact) {
        const meta = parsePeekMeta(raw, notePath.split(/[\\/]/).pop() ?? notePath);
        previewBody = stripLiftedPeekMeta(parts.body, meta);
      }
      previewHtml = markdownBodyToHtml(previewBody);

      if (compact || viewMode === "preview") {
        return;
      }

      await tick();
      if (!editorEl) {
        throw new Error("Editor surface not ready — try switching to Edit view");
      }

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
    } catch (e) {
      error = formatError(e);
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

  $effect(() => {
    if (path === loadedPath) return;
    loadedPath = path;
    void initEditorForPath(path);
  });

  $effect(() => {
    const editor = editorEl;
    const preview = previewEl;
    editor?.addEventListener("click", handlePreviewClick);
    preview?.addEventListener("click", handlePreviewClick);
    return () => {
      editor?.removeEventListener("click", handlePreviewClick);
      preview?.removeEventListener("click", handlePreviewClick);
    };
  });

  onDestroy(() => {
    if (previewTimer) clearTimeout(previewTimer);
    editor?.destroy();
    editor = null;
  });
</script>

<section class="note-editor" class:compact>
  {#if !compact}
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
  {/if}

  {#if loading}
    <div class="loading">Loading note…</div>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div
    class="editor-layout"
    class:split={!compact && viewMode === "split"}
    class:preview-only={compact || viewMode === "preview"}
    class:dimmed={loading}
    class:hidden={!!error}
  >
    {#if !compact && viewMode !== "preview"}
      <div class="editor-wrap" style={viewMode === "split" ? `flex: ${splitRatio}` : ""} bind:this={editorEl}></div>
    {/if}
    {#if !compact && viewMode === "split"}
      <PaneResizer onResize={onSplitResize} />
    {/if}
    {#if compact || viewMode !== "edit"}
      <div
        class="preview-wrap"
        style={viewMode === "split" ? `flex: ${1 - splitRatio}` : ""}
        bind:this={previewEl}
      >
        {@html previewHtml}
      </div>
    {/if}
  </div>

  {#if saveMessage && !compact}
    <p class="save-msg" class:error={saveMessage !== "Saved"}>{saveMessage}</p>
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
    font-size: var(--text-base);
    font-weight: var(--font-medium);
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

  .editor-layout.dimmed {
    opacity: 0.45;
    pointer-events: none;
  }

  .editor-wrap,
  .preview-wrap {
    background: var(--bg-elevated);
    overflow-y: auto;
    padding: 2.25rem 2.75rem 3.25rem;
    flex: 1;
    min-height: 0;
  }

  .note-editor.compact .preview-wrap {
    padding: 0.85rem 1rem 1.4rem;
    background: transparent;
    font-size: var(--text-base);
    line-height: 1.65;
    color: var(--text);
  }

  .note-editor.compact .preview-wrap :global(h1) {
    font-size: var(--text-lg);
    font-weight: 650;
    letter-spacing: -0.02em;
    line-height: 1.3;
    margin: 0 0 0.7rem;
    color: var(--text);
  }

  .note-editor.compact .preview-wrap :global(h2),
  .note-editor.compact .preview-wrap :global(h3) {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    margin: 1rem 0 0.4rem;
    color: var(--text);
  }

  .note-editor.compact .preview-wrap :global(p) {
    margin: 0 0 0.75rem;
    color: var(--text);
  }

  .note-editor.compact .preview-wrap :global(ul),
  .note-editor.compact .preview-wrap :global(ol) {
    padding-left: 1.2rem;
    margin: 0 0 0.75rem;
  }

  .note-editor.compact .preview-wrap :global(li) {
    margin-bottom: 0.35rem;
    color: var(--text);
  }

  .note-editor.compact .preview-wrap :global(blockquote) {
    margin: 0 0 0.85rem;
    padding: 0.55rem 0.7rem;
    border-left: 2px solid var(--border-active);
    background: var(--control-fill);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    color: var(--text-muted);
    font-style: italic;
  }

  .note-editor.compact .preview-wrap :global(blockquote p) {
    margin: 0;
    color: var(--text-muted);
  }

  .note-editor.compact .preview-wrap :global(em) {
    color: var(--text-muted);
  }

  .note-editor.compact .preview-wrap :global(a:not(.wikilink)) {
    display: block;
    width: fit-content;
    max-width: 100%;
    margin: 0 0 0.75rem;
    color: var(--accent-link);
    font-size: var(--text-sm);
    text-decoration: underline;
    text-underline-offset: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .note-editor.compact .preview-wrap :global(a:not(.wikilink):hover) {
    color: var(--text);
  }

  .preview-wrap :global(> *:first-child) {
    margin-top: 0;
  }

  .preview-wrap :global(> *:last-child) {
    margin-bottom: 0;
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
    font-size: var(--text-xs);
    color: var(--success);
    border-top: 1px solid var(--border-subtle);
  }

  .save-msg.error {
    color: var(--error);
  }

  .loading {
    padding: 1rem;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .error {
    padding: 0.75rem;
    font-size: var(--text-sm);
    color: var(--error);
  }
</style>