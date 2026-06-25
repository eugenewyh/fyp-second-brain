<script lang="ts">
  import { tabs } from "$lib/stores/tabs.svelte";

  function icon(type: string): string {
    switch (type) {
      case "research":
        return "🔬";
      case "query":
        return "💬";
      case "note":
        return "📝";
      case "ingest":
        return "📁";
      case "settings":
        return "⚙️";
      default:
        return "•";
    }
  }
</script>

<div class="tab-bar">
  {#each tabs.tabs as tab (tab.id)}
    <button
      class="tab"
      class:active={tabs.activeTabId === tab.id}
      onclick={() => tabs.activate(tab.id)}
    >
      <span class="tab-icon">{icon(tab.type)}</span>
      <span class="tab-label">{tab.label}</span>
      {#if tabs.tabs.length > 1}
        <span
          class="tab-close"
          role="button"
          tabindex="0"
          onclick={(e) => {
            e.stopPropagation();
            tabs.closeTab(tab.id);
          }}
          onkeydown={(e) => {
            if (e.key === "Enter") {
              e.stopPropagation();
              tabs.closeTab(tab.id);
            }
          }}
        >×</span>
      {/if}
    </button>
  {/each}
</div>

<style>
  .tab-bar {
    display: flex;
    gap: 2px;
    padding: 0.4rem 0.5rem 0;
    background: var(--pane-bg, var(--bg));
    border-bottom: 1px solid var(--border);
    overflow-x: auto;
    flex-shrink: 0;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.45rem 0.7rem;
    background: transparent;
    color: var(--text-muted);
    border-radius: var(--radius) var(--radius) 0 0;
    font-size: 0.8rem;
    white-space: nowrap;
  }

  .tab:hover {
    background: var(--surface-hover);
    color: var(--text);
  }

  .tab.active {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-bottom-color: var(--surface);
    margin-bottom: -1px;
  }

  .tab-close {
    opacity: 0.5;
    font-size: 1rem;
    line-height: 1;
    padding: 0 0.15rem;
  }

  .tab-close:hover {
    opacity: 1;
    color: var(--error);
  }
</style>