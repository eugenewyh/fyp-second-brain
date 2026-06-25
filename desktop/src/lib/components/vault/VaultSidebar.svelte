<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import {
    shouldUseSemanticSearch,
    fuzzySearchHits,
    semanticSearchHits,
  } from "$lib/vault/search-dispatch";
  import type { VaultSearchHit } from "$lib/vault/types";
  import type { VaultNode } from "$lib/vault/types";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import VaultSearch from "./VaultSearch.svelte";
  import VaultTree from "./VaultTree.svelte";
  import GraphMini from "./GraphMini.svelte";
  import VaultStatus from "./VaultStatus.svelte";

  let nodes = $state<VaultNode[]>([]);
  let loading = $state(true);
  let searchLoading = $state(false);
  let searchHits = $state<VaultSearchHit[]>([]);
  let searchError = $state("");

  async function refreshTree() {
    loading = true;
    try {
      workspace.vaultRoot = await getVaultRoot();
      nodes = await loadVaultTree(workspace.vaultRoot);
    } finally {
      loading = false;
    }
  }

  async function onSearch(query: string) {
    searchError = "";
    if (!query.trim()) {
      searchHits = [];
      return;
    }

    if (shouldUseSemanticSearch(workspace.vaultSearchMode)) {
      if (!connection.connected) {
        searchError = "Sidecar offline — semantic search unavailable";
        searchHits = [];
        return;
      }
      searchLoading = true;
      try {
        const res = await api.vaultSearch(query.trim());
        searchHits = semanticSearchHits(res.results);
      } catch (e) {
        searchError = e instanceof Error ? e.message : "Semantic search failed";
        searchHits = [];
      } finally {
        searchLoading = false;
      }
    } else {
      searchHits = fuzzySearchHits(nodes, query);
    }
  }

  function openHit(hit: VaultSearchHit) {
    tabs.openNoteTab(hit.path, hit.name);
    workspace.setActiveNote(hit.path);
  }

  let lastRefreshNonce = 0;
  $effect(() => {
    const nonce = workspace.vaultRefreshNonce;
    if (nonce > 0 && nonce !== lastRefreshNonce) {
      lastRefreshNonce = nonce;
      refreshTree();
    }
  });

  onMount(() => {
    refreshTree();
  });
</script>

<aside class="vault-sidebar">
  <div class="header">
    <h2>Vault</h2>
    <button class="collapse-btn" onclick={() => workspace.toggleLeft()} title="Collapse">◀</button>
  </div>

  <VaultSearch onSearch={onSearch} />

  <div class="tree-area">
    {#if loading}
      <p class="loading">Loading vault…</p>
    {:else if searchLoading}
      <p class="loading">Searching embeddings…</p>
    {:else if searchError}
      <p class="search-error">{searchError}</p>
    {:else if searchHits.length}
      <ul class="search-results">
        {#each searchHits as hit (hit.path)}
          <li>
            <button onclick={() => openHit(hit)}>
              <span class="hit-name">{hit.name}</span>
              {#if hit.excerpt}
                <span class="hit-excerpt">{hit.excerpt.slice(0, 100)}…</span>
              {/if}
            </button>
          </li>
        {/each}
      </ul>
    {:else if workspace.vaultSearchQuery.trim()}
      <p class="empty">No results</p>
    {:else}
      <VaultTree {nodes} filter={workspace.vaultSearchQuery} />
    {/if}
  </div>

  <GraphMini />
  <VaultStatus />
</aside>

<style>
  .vault-sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--pane-bg, var(--surface));
    overflow: hidden;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.65rem 0.75rem;
    border-bottom: 1px solid var(--border);
  }

  .header h2 {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .collapse-btn {
    background: transparent;
    color: var(--text-muted);
    padding: 0.2rem 0.4rem;
    font-size: 0.75rem;
  }

  .tree-area {
    flex: 1;
    overflow-y: auto;
    padding: 0.35rem 0;
  }

  .loading,
  .empty {
    padding: 1rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .search-error {
    padding: 0.75rem;
    font-size: 0.75rem;
    color: var(--error);
  }

  .search-results {
    list-style: none;
    padding: 0.25rem 0.5rem;
  }

  .search-results button {
    width: 100%;
    text-align: left;
    padding: 0.4rem 0.5rem;
    background: transparent;
    color: var(--text);
    font-size: 0.8rem;
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .search-results button:hover {
    background: var(--surface-hover);
  }

  .hit-name {
    font-weight: 500;
  }

  .hit-excerpt {
    font-size: 0.7rem;
    color: var(--text-muted);
  }
</style>