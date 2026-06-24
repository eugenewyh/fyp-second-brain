<script lang="ts">
  import { onMount } from "svelte";
  import { filterVaultTree, loadVaultTree } from "$lib/vault/load";
  import type { VaultNode } from "$lib/vault/types";
  import { VAULT_ROOT_LABEL } from "$lib/vault/types";

  interface Props {
    collectionCount: number;
    connected: boolean;
    connectionError: string;
    onRetry: () => void;
    fuzzyQuery?: string;
    semanticQuery?: string;
    onFuzzyChange?: (value: string) => void;
    onSemanticChange?: (value: string) => void;
  }

  let {
    collectionCount,
    connected,
    connectionError,
    onRetry,
    fuzzyQuery = $bindable(""),
    semanticQuery = $bindable(""),
    onFuzzyChange,
    onSemanticChange,
  }: Props = $props();

  let vaultTree = $state<VaultNode[]>([]);
  let vaultLoading = $state(true);

  const displayTree = $derived(filterVaultTree(vaultTree, fuzzyQuery));

  onMount(async () => {
    vaultLoading = true;
    vaultTree = await loadVaultTree();
    vaultLoading = false;
  });
</script>

<aside class="vault-sidebar" data-testid="vault-sidebar">
  <section class="section">
    <h3 class="section-title">Vault</h3>
    <div class="vault-tree" data-testid="vault-tree" data-vault-root={VAULT_ROOT_LABEL}>
      {#if vaultLoading}
        <p class="tree-status">Loading vault…</p>
      {:else if displayTree.length === 0}
        <p class="tree-status">No files in {VAULT_ROOT_LABEL}</p>
      {:else}
        {#each displayTree as node}
          <div class="tree-folder">
            <span class="tree-icon">📁</span>
            <span>{node.name}</span>
          </div>
          {#if node.children}
            {#each node.children as child}
              <div class="tree-entry nested" class:tree-folder={child.type === "folder"} class:tree-file={child.type === "file"}>
                <span class="tree-icon">{child.type === "folder" ? "📁" : "📄"}</span>
                <span>{child.name}</span>
              </div>
              {#if child.children}
                {#each child.children as grandchild}
                  <div class="tree-entry nested-2" class:tree-folder={grandchild.type === "folder"} class:tree-file={grandchild.type === "file"}>
                    <span class="tree-icon">{grandchild.type === "folder" ? "📁" : "📄"}</span>
                    <span>{grandchild.name}</span>
                  </div>
                {/each}
              {/if}
            {/each}
          {/if}
        {/each}
      {/if}
    </div>
  </section>

  <section class="section">
    <h3 class="section-title">Search</h3>
    <label class="search-field">
      <span>Fuzzy search</span>
      <input
        type="text"
        placeholder="Filter vault files…"
        bind:value={fuzzyQuery}
        oninput={() => onFuzzyChange?.(fuzzyQuery)}
        data-testid="fuzzy-search"
      />
    </label>
    <label class="search-field">
      <span>Semantic search</span>
      <input
        type="text"
        placeholder="Search knowledge base…"
        bind:value={semanticQuery}
        oninput={() => onSemanticChange?.(semanticQuery)}
        data-testid="semantic-search"
      />
    </label>
  </section>

  <section class="section graph-section">
    <h3 class="section-title">Graph Overview</h3>
    <div class="graph-placeholder" data-testid="graph-overview" aria-label="Mini graph overview">
      <svg viewBox="0 0 120 80" class="graph-svg">
        <circle cx="60" cy="40" r="8" fill="var(--accent)" opacity="0.9" />
        <circle cx="30" cy="25" r="5" fill="var(--text-muted)" opacity="0.6" />
        <circle cx="90" cy="25" r="5" fill="var(--text-muted)" opacity="0.6" />
        <circle cx="25" cy="60" r="5" fill="var(--text-muted)" opacity="0.6" />
        <circle cx="95" cy="60" r="5" fill="var(--text-muted)" opacity="0.6" />
        <line x1="60" y1="40" x2="30" y2="25" stroke="var(--border)" stroke-width="1.5" />
        <line x1="60" y1="40" x2="90" y2="25" stroke="var(--border)" stroke-width="1.5" />
        <line x1="60" y1="40" x2="25" y2="60" stroke="var(--border)" stroke-width="1.5" />
        <line x1="60" y1="40" x2="95" y2="60" stroke="var(--border)" stroke-width="1.5" />
      </svg>
      <p class="graph-caption">Knowledge graph preview</p>
    </div>
  </section>

  <section class="section ingest-section">
    <h3 class="section-title">Ingest Status</h3>
    <div class="ingest-status" data-testid="ingest-status">
      <span class="status-dot" class:online={connected}></span>
      {#if connected}
        <span>{collectionCount} chunks indexed</span>
      {:else}
        <span>Disconnected</span>
      {/if}
    </div>
    {#if connectionError}
      <p class="error-text">{connectionError}</p>
      <button class="btn-secondary retry-btn" onclick={onRetry}>Retry</button>
    {/if}
  </section>
</aside>

<style>
  .vault-sidebar {
    height: 100%;
    overflow-y: auto;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-title {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }

  .vault-tree {
    font-size: 0.8rem;
    color: var(--text);
  }

  .tree-status {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .tree-folder,
  .tree-file,
  .tree-entry {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0;
    cursor: default;
  }

  .nested {
    padding-left: 0.85rem;
  }

  .nested-2 {
    padding-left: 1.7rem;
  }

  .tree-icon {
    font-size: 0.75rem;
    opacity: 0.8;
  }

  .search-field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .search-field input {
    font-size: 0.8rem;
    padding: 0.45rem 0.6rem;
  }

  .graph-placeholder {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.5rem;
    text-align: center;
  }

  .graph-svg {
    width: 100%;
    height: 70px;
  }

  .graph-caption {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
  }

  .ingest-status {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--error);
    flex-shrink: 0;
  }

  .status-dot.online {
    background: var(--success);
  }

  .error-text {
    color: var(--error);
    font-size: 0.7rem;
    margin-top: 0.4rem;
  }

  .retry-btn {
    margin-top: 0.5rem;
    width: 100%;
    font-size: 0.75rem;
    padding: 0.4rem;
  }
</style>