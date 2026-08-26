<script lang="ts">
  import { X } from "@lucide/svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import NoteEditor from "$lib/components/editor/NoteEditor.svelte";
  import PdfViewer from "$lib/components/editor/PdfViewer.svelte";
  import EditorPlaceholder from "$lib/components/editor/EditorPlaceholder.svelte";
  import { isPdfPath } from "$lib/vault/pdf";

  interface Props {
    peek?: boolean;
    chrome?: boolean;
    compact?: boolean;
  }

  let { peek = false, chrome = true, compact = false }: Props = $props();

  const path = $derived(app.documentPath);
  const title = $derived(app.documentLabel ?? path?.split(/[\\/]/).pop() ?? "Document");
</script>

<div class="document" class:peek data-testid="pane-center">
  {#if chrome}
  <header class="doc-header" data-tauri-drag-region>
    {#if peek}
      <span class="title" title={path ?? undefined}>{title}</span>
      <button type="button" class="link" onclick={() => workspace.setKnowledgePanel(true)}>
        Files
      </button>
      <button
        type="button"
        class="icon-close"
        title="Close"
        aria-label="Close document"
        onclick={() => app.closeDocument()}
      >
        <X size={16} />
      </button>
    {:else}
      <button type="button" class="back" onclick={() => app.backFromDocument()}>← Back</button>
      <span class="title" title={path ?? undefined}>{title}</span>
      <button type="button" class="link" onclick={() => workspace.setKnowledgePanel(true)}>
        Files
      </button>
    {/if}
  </header>
  {/if}

  <div class="doc-body">
    {#if path}
      {#if path.endsWith(".md")}
        {#key path}
          <NoteEditor {path} {compact} />
        {/key}
      {:else if isPdfPath(path)}
        {#key `${path}:${app.documentGeneration}`}
          <PdfViewer {path} />
        {/key}
      {:else}
        <EditorPlaceholder {path} />
      {/if}
    {/if}
  </div>
</div>

<style>
  .document {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--bg);
  }

  .doc-header {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0 1rem;
    min-height: var(--titlebar-height);
    flex-shrink: 0;
    position: relative;
    z-index: 5;
    -webkit-app-region: drag;
    app-region: drag;
  }
  .doc-header :global(button) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .back,
  .link {
    background: transparent;
    color: var(--text-faint);
    font-size: var(--text-base);
    font-weight: var(--font-normal);
    min-height: auto;
    padding: 0.25rem 0;
    flex-shrink: 0;
  }

  .back:hover,
  .link:hover {
    color: var(--text);
  }

  .icon-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-faint);
    padding: 0.2rem;
    cursor: pointer;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
  }

  .icon-close:hover {
    color: var(--text);
    background: var(--surface-hover);
  }

  .title {
    flex: 1;
    font-size: var(--text-base);
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .doc-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
</style>
