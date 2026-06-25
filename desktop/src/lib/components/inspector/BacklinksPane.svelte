<script lang="ts">
  import { api } from "$lib/api";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";

  let related = $state<{ source: string; excerpt: string; distance?: number }[]>([]);
  let loading = $state(false);

  async function loadRelated() {
    if (!workspace.activeNotePath || !connection.connected) return;
    loading = true;
    try {
      const name = workspace.activeNotePath.split("/").pop() ?? "";
      const result = await api.vaultRelated(name, 5);
      related = result.results;
    } catch {
      related = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (workspace.activeNotePath && connection.connected) {
      loadRelated();
    }
  });
</script>

<div class="backlinks">
  <h4>Related notes</h4>
  {#if loading}
    <p class="hint">Searching embeddings…</p>
  {:else if related.length}
    <ul>
      {#each related as item}
        <li>
          <button onclick={() => tabs.openNoteTab(item.source, item.source.split("/").pop())}>
            {item.source.split("/").pop()}
          </button>
          <p class="excerpt">{item.excerpt.slice(0, 120)}…</p>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="hint">Select a note to see Chroma-related chunks</p>
  {/if}
</div>

<style>
  .backlinks {
    padding: 0.75rem;
    font-size: 0.8rem;
    overflow-y: auto;
    height: 100%;
  }

  h4 {
    font-size: 0.75rem;
    color: var(--accent);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  ul {
    list-style: none;
  }

  li {
    margin-bottom: 0.65rem;
  }

  button {
    background: transparent;
    color: var(--text);
    padding: 0;
    font-size: 0.85rem;
    text-align: left;
  }

  button:hover {
    color: var(--accent);
  }

  .excerpt {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.75rem;
  }
</style>