<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";

  interface Props {
    onSearch?: (query: string) => void;
  }

  let { onSearch }: Props = $props();

  function onInput() {
    onSearch?.(workspace.vaultSearchQuery);
  }

  function setMode(mode: "fuzzy" | "semantic") {
    workspace.vaultSearchMode = mode;
    onSearch?.(workspace.vaultSearchQuery);
  }
</script>

<div class="vault-search">
  <input
    data-vault-search
    bind:value={workspace.vaultSearchQuery}
    placeholder="Search vault…"
    oninput={onInput}
  />
  <div class="mode-toggle">
    <button
      class="mode-btn"
      class:active={workspace.vaultSearchMode === "fuzzy"}
      onclick={() => setMode("fuzzy")}
    >
      Fuzzy
    </button>
    <button
      class="mode-btn"
      class:active={workspace.vaultSearchMode === "semantic"}
      onclick={() => setMode("semantic")}
    >
      Semantic
    </button>
  </div>
  {#if workspace.vaultSearchMode === "semantic"}
    <p class="badge">Semantic search uses Chroma embeddings via sidecar</p>
  {/if}
</div>

<style>
  .vault-search {
    padding: 0.5rem 0.65rem;
    border-bottom: 1px solid var(--border);
  }

  .vault-search input {
    font-size: 0.8rem;
    padding: 0.45rem 0.6rem;
  }

  .mode-toggle {
    display: flex;
    gap: 0.25rem;
    margin-top: 0.4rem;
  }

  .mode-btn {
    flex: 1;
    padding: 0.3rem;
    font-size: 0.7rem;
    background: var(--bg);
    color: var(--text-muted);
    border: 1px solid var(--border);
  }

  .mode-btn.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  .badge {
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 0.35rem;
  }
</style>