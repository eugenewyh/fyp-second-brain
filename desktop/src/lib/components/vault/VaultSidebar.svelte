<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import {
    shouldUseSemanticSearch,
    fuzzySearchHits,
    semanticSearchHits,
  } from "$lib/vault/search-dispatch";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import type { VaultSearchHit } from "$lib/vault/types";
  import type { VaultNode } from "$lib/vault/types";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import VaultSearch from "./VaultSearch.svelte";
  import VaultTree from "./VaultTree.svelte";
  import GraphMini from "./GraphMini.svelte";
  import VaultStatus from "./VaultStatus.svelte";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { PanelLeftClose } from "@lucide/svelte";

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
        searchError = "Sidecar offline";
        searchHits = [];
        return;
      }
      searchLoading = true;
      try {
        const res = await api.vaultSearch(query.trim());
        searchHits = semanticSearchHits(res.results, flattenVaultFiles(nodes));
      } catch (e) {
        searchError = e instanceof Error ? e.message : "Search failed";
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
    <SectionLabel>Vault</SectionLabel>
    <Button variant="icon" title="Collapse" onclick={() => workspace.toggleLeft()}>
      <PanelLeftClose size={15} strokeWidth={1.75} />
    </Button>
  </div>

  <VaultSearch onSearch={onSearch} />

  <div class="tree-area ui-scroll">
    {#if loading}
      <p class="ui-empty">Loading…</p>
    {:else if searchLoading}
      <p class="ui-empty">Searching…</p>
    {:else if searchError}
      <p class="search-error">{searchError}</p>
    {:else if searchHits.length}
      <ul class="search-results">
        {#each searchHits as hit (hit.path)}
          <li>
            <button class="ui-list-item" onclick={() => openHit(hit)}>
              <span class="hit-name">{hit.name}</span>
              {#if hit.excerpt}
                <span class="hit-excerpt">{hit.excerpt.slice(0, 80)}…</span>
              {/if}
            </button>
          </li>
        {/each}
      </ul>
    {:else if workspace.vaultSearchQuery.trim()}
      <p class="ui-empty">No results</p>
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
    background: var(--pane-bg);
    overflow: hidden;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.55rem 0.65rem;
    border-bottom: 1px solid var(--border-subtle);
    min-height: 36px;
  }

  .tree-area {
    flex: 1;
    padding: 0.25rem 0.35rem;
  }

  .search-error {
    padding: 0.75rem;
    font-size: 0.7rem;
    color: var(--error);
  }

  .search-results {
    list-style: none;
  }

  .search-results .ui-list-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
  }

  .hit-name {
    font-weight: 500;
    color: var(--text);
  }

  .hit-excerpt {
    font-size: 0.65rem;
    color: var(--text-faint);
  }
</style>