<script lang="ts">
  import { api } from "$lib/api";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import GraphView from "./GraphView.svelte";

  let hasMemory = $state(false);
  let filing = $state(false);

  const topic = $derived(workspace.activeTopicPath);
  const topicName = $derived(topic?.split(/[\\/]/).pop()?.replace(/[-_]/g, " ") ?? "Topic");

  async function checkMemory() {
    if (!topic) {
      hasMemory = false;
      return;
    }
    try {
      const w = await api.listWatches(topic);
      hasMemory = w.has_memory;
    } catch {
      hasMemory = false;
    }
  }

  $effect(() => {
    void topic;
    void workspace.vaultRefreshNonce;
    void checkMemory();
  });

  async function fileTopicNotes() {
    if (!topic || filing) return;
    filing = true;
    try {
      await assistant.rememberTopicNotes(topic);
      await checkMemory();
    } finally {
      filing = false;
    }
  }
</script>

<div class="memory-home">
  <header class="memory-bar" data-tauri-drag-region>
    <span class="title">Memory</span>
    <span class="topic">{topicName}</span>
  </header>
  <div class="memory-body">
    {#if hasMemory}
      <GraphView />
    {:else}
      <div class="empty">
        <p>Nothing saved from your notes yet. Notes already in this topic can be filed.</p>
        <button type="button" class="file-btn" disabled={filing} onclick={() => void fileTopicNotes()}>
          {filing ? "Filing…" : "File notes in this topic"}
        </button>
      </div>
    {/if}
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

  .topic {
    font-size: var(--text-sm);
    color: var(--text-muted);
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

  .empty {
    margin: auto;
    max-width: 18rem;
    text-align: center;
    color: var(--text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  .file-btn {
    font-size: var(--text-sm);
    border: 1px solid var(--border);
    background: var(--control-fill);
    color: var(--text);
    padding: 0.3rem 0.7rem;
    border-radius: var(--radius-md);
    cursor: pointer;
  }

  .file-btn:disabled {
    opacity: 0.5;
    cursor: wait;
  }
</style>
