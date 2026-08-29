<script lang="ts">
  import { app } from "$lib/stores/app.svelte";
  import GraphView from "./GraphView.svelte";
</script>

<div class="memory-home">
  <header class="memory-bar" data-tauri-drag-region>
    <span class="title">Memory</span>
  </header>
  <div class="memory-body">
    <GraphView initialTopicPath={app.memoryTopicFilter} />
  </div>
</div>

<style>
  .memory-home {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--bg);
  }

  .memory-bar {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-height: var(--titlebar-height);
    padding: 0 1rem;
    position: relative;
    z-index: 5;
    background: var(--bg);
    -webkit-app-region: drag;
    app-region: drag;
  }

  .title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text);
  }

  .memory-body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .memory-body :global(.graph-view) {
    flex: 1;
    min-height: 0;
  }
</style>
