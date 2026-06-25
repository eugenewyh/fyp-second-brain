<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";

  function openPath(path: string) {
    tabs.openNoteTab(path);
    workspace.setActiveNote(path);
  }
</script>

<div class="graph-mini">
  <h3>Recently touched</h3>
  {#if workspace.recentNotePaths.length}
    <ul>
      {#each workspace.recentNotePaths as path}
        <li>
          <button onclick={() => openPath(path)}>{path.split("/").pop()}</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty">Open a note to see history</p>
  {/if}

  <h3>Suggested connections</h3>
  <p class="empty">Backlinks & embeddings — Phase 2</p>
</div>

<style>
  .graph-mini {
    padding: 0.65rem;
    border-top: 1px solid var(--border);
    font-size: 0.75rem;
  }

  .graph-mini h3 {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.35rem;
  }

  .graph-mini h3:not(:first-child) {
    margin-top: 0.75rem;
  }

  .graph-mini ul {
    list-style: none;
  }

  .graph-mini button {
    width: 100%;
    text-align: left;
    padding: 0.3rem 0.4rem;
    background: transparent;
    color: var(--text);
    font-size: 0.75rem;
    border-radius: 4px;
  }

  .graph-mini button:hover {
    background: var(--surface-hover);
  }

  .empty {
    color: var(--text-muted);
    font-size: 0.7rem;
  }
</style>