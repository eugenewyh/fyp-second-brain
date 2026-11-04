<script lang="ts">
  import { app } from "$lib/stores/app.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { memory } from "$lib/stores/memory.svelte";
  import GraphView from "./GraphView.svelte";
  import DocumentView from "./DocumentView.svelte";
  import PaneResizer from "$lib/components/workspace/PaneResizer.svelte";
  import {
    clampPeekWidth,
    loadPeekWidth,
    savePeekWidth,
  } from "$lib/workspace/layout-prefs";

  const showDocPeek = $derived(app.isDocumentPeek && app.isMemory);
  const scopeLabel = $derived(
    memory.topicFilter?.split(/[/\\]/).filter(Boolean).pop() || "All workspaces",
  );

  let peekWidth = $state(loadPeekWidth());

  function onPeekResize(delta: number) {
    peekWidth = clampPeekWidth(peekWidth - delta);
  }

  function onPeekResizeEnd() {
    savePeekWidth(peekWidth);
  }
</script>

<div class="memory-home">
  <div class="memory-col">
    <header class="memory-header" data-tauri-drag-region>
      <span class="title">{scopeLabel}</span>
      {#if connection.connectionError}
        <p class="netbar" role="status">
          <span>{connection.connectionError}</span>
          <button type="button" onclick={() => void connection.reloadService()}>Retry</button>
        </p>
      {:else if connection.connecting}
        <p class="netbar" role="status">Connecting to the AI service…</p>
      {/if}
    </header>
    <GraphView />
  </div>
  {#if showDocPeek}
    <PaneResizer
      onResize={onPeekResize}
      onResizeEnd={onPeekResizeEnd}
      testId="splitter-memory-peek"
    />
    <aside class="peek-pane" style="width: {peekWidth}px" aria-label="Note">
      <DocumentView peek />
    </aside>
  {/if}
</div>

<style>
  .memory-home {
    display: flex;
    height: 100%;
    min-height: 0;
    background: var(--bg);
  }

  .memory-col {
    flex: 1;
    min-width: 18rem;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .memory-header {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    min-height: var(--titlebar-height);
    padding: 0 1rem;
    position: relative;
    z-index: 5;
    background: var(--bg);
    border-bottom: 1px solid var(--border-subtle);
    -webkit-app-region: drag;
    app-region: drag;
  }

  .title {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
    line-height: 1.3;
    letter-spacing: -0.01em;
  }

  .netbar {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 0.65rem;
    max-width: min(36rem, 70%);
    color: var(--text-muted);
    font-size: var(--text-sm);
    -webkit-app-region: no-drag;
  }

  .netbar button {
    background: transparent;
    color: var(--accent-live);
    min-height: auto;
    padding: 0.15rem 0.35rem;
  }

  .netbar button:hover {
    background: var(--accent-live-dim);
  }

  .memory-col :global(.graph-view) {
    flex: 1;
    min-height: 0;
  }

  .peek-pane {
    flex-shrink: 0;
    max-width: 40%;
    border-left: 1px solid var(--border-subtle);
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }

  .peek-pane :global(.document) {
    flex: 1;
    min-height: 0;
  }
</style>
