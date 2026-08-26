<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { app } from "$lib/stores/app.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import {
    shouldUseSemanticSearch,
    fuzzySearchHits,
    semanticSearchHits,
  } from "$lib/vault/search-dispatch";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import {
    topicsFromTree,
    treeForTopic,
    filesForTopic,
    recentInTopic,
  } from "$lib/vault/topics";
  import type { VaultNode, VaultSearchHit } from "$lib/vault/types";
  import VaultTree from "$lib/components/vault/VaultTree.svelte";

  let nodes = $state<VaultNode[]>([]);
  let loading = $state(true);
  let query = $state("");
  let searchHits = $state<VaultSearchHit[]>([]);
  let searchError = $state("");
  let searchLoading = $state(false);
  let tab = $state<"docs" | "research" | "topics">("docs");

  const topics = $derived(topicsFromTree(nodes));
  const activeTopic = $derived(
    workspace.activeTopicPath
      ? topics.find((t) => t.path === workspace.activeTopicPath) ?? null
      : null,
  );
  const displayNodes = $derived(treeForTopic(nodes, workspace.activeTopicPath));
  const topicFiles = $derived(filesForTopic(nodes, workspace.activeTopicPath));
  const recentPaths = $derived(
    recentInTopic(workspace.recentNotePaths, workspace.activeTopicPath),
  );

  const pastResearch = $derived.by(() => {
    const all = flattenVaultFiles(nodes);
    return all
      .filter(
        (f) =>
          f.path.includes("/research/") ||
          f.path.includes("\\research\\") ||
          /research/i.test(f.name),
      )
      .slice(-12)
      .reverse();
  });

  async function refresh() {
    loading = true;
    try {
      workspace.vaultRoot = await getVaultRoot();
      nodes = await loadVaultTree(workspace.vaultRoot);
    } finally {
      loading = false;
    }
  }

  async function onSearch() {
    searchError = "";
    if (!query.trim()) {
      searchHits = [];
      return;
    }
    if (shouldUseSemanticSearch(workspace.vaultSearchMode)) {
      if (!connection.connected) {
        searchError = "Connect AI for semantic search";
        return;
      }
      searchLoading = true;
      try {
        const res = await api.vaultSearch(query.trim());
        const hits = semanticSearchHits(res.results, flattenVaultFiles(nodes));
        const allowed = new Set(topicFiles.map((f) => f.path));
        searchHits = workspace.activeTopicPath
          ? hits.filter((h) => allowed.has(h.path))
          : hits;
      } catch (e) {
        searchError = e instanceof Error ? e.message : "Search failed";
      } finally {
        searchLoading = false;
      }
    } else {
      searchHits = fuzzySearchHits(
        workspace.activeTopicPath
          ? [
              {
                name: activeTopic?.name ?? "topic",
                path: workspace.activeTopicPath,
                type: "folder",
                children: displayNodes,
              },
            ]
          : nodes,
        query,
      );
    }
  }

  function openFile(path: string, name?: string) {
    app.openDocument(path, { label: name, from: "agent" });
    workspace.setActiveNote(path);
  }

  function selectTopic(path: string | null) {
    workspace.setActiveTopic(path);
    tab = "docs";
    query = "";
    searchHits = [];
  }

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void refresh();
  });

  onMount(() => {
    void refresh();
  });
</script>

<aside class="panel" aria-label="Your knowledge">
  <div class="panel-head" data-tauri-drag-region>
    <span class="title">Vault</span>
    <div class="head-actions">
      <button type="button" class="graph-link" onclick={() => app.openHome()} title="Home">
        Home
      </button>
      <button
        type="button"
        class="x"
        aria-label="Close library"
        onclick={() => workspace.setKnowledgePanel(false)}
      >
        ✕
      </button>
    </div>
  </div>

  <p class="growth">
    {#if connection.collectionCount > 0}
      {connection.collectionCount.toLocaleString()} pages
    {:else}
      Empty — ingest documents
    {/if}
  </p>

  <div class="tabs">
    <button type="button" class:active={tab === "docs"} onclick={() => (tab = "docs")}>
      Documents
    </button>
    <button type="button" class:active={tab === "research"} onclick={() => (tab = "research")}>
      Past research
    </button>
    <button type="button" class:active={tab === "topics"} onclick={() => (tab = "topics")}>
      Topics
    </button>
  </div>

  {#if tab === "docs"}
    <div class="search">
      <input
        data-vault-search
        bind:value={query}
        placeholder="Search your library…"
        oninput={() => void onSearch()}
      />
    </div>
  {/if}

  <div class="body ui-scroll">
    {#if tab === "topics"}
      <p class="sec">Knowledge spaces</p>
      <button
        type="button"
        class="row"
        class:on={!workspace.activeTopicPath}
        onclick={() => selectTopic(null)}
      >
        All knowledge
      </button>
      {#each topics as t (t.path)}
        <button
          type="button"
          class="row"
          class:on={workspace.activeTopicPath === t.path}
          onclick={() => selectTopic(t.path)}
        >
          {t.name}
        </button>
      {/each}
      {#if topics.length === 0}
        <p class="muted">Top-level folders become topics.</p>
      {/if}
    {:else if tab === "research"}
      <p class="sec">Research written back into memory</p>
      {#if pastResearch.length === 0}
        <p class="muted">
          After Deep research, reports auto-save here. That’s how knowledge compounds — unlike a
          disposable chat.
        </p>
      {:else}
        <ul class="list">
          {#each pastResearch as f (f.path)}
            <li>
              <button type="button" class="row" onclick={() => openFile(f.path, f.name)}>
                {f.name}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    {:else}
      {#if !query.trim() && recentPaths.length}
        <p class="sec">Recent</p>
        <ul class="list">
          {#each recentPaths as p (p)}
            <li>
              <button type="button" class="row" onclick={() => openFile(p)}>
                {p.split("/").pop()}
              </button>
            </li>
          {/each}
        </ul>
      {/if}

      <p class="sec">{activeTopic ? activeTopic.name : "All documents"}</p>
      {#if loading}
        <p class="muted">…</p>
      {:else if searchLoading}
        <p class="muted">Searching…</p>
      {:else if searchError}
        <p class="err">{searchError}</p>
      {:else if searchHits.length}
        <ul class="list">
          {#each searchHits as hit (hit.path)}
            <li>
              <button type="button" class="row" onclick={() => openFile(hit.path, hit.name)}>
                {hit.name}
              </button>
            </li>
          {/each}
        </ul>
      {:else if query.trim()}
        <p class="muted">No matches in your library</p>
      {:else if displayNodes.length === 0}
        <p class="muted">No files yet</p>
        <button type="button" class="add" onclick={() => app.openSheet("ingest")}>
          Add knowledge
        </button>
      {:else}
        <div class="tree">
          <VaultTree nodes={displayNodes} filter="" />
        </div>
      {/if}
    {/if}
  </div>
</aside>

<style>
  .panel {
    width: min(300px, 28vw);
    flex-shrink: 0;
    border-left: 1px solid var(--border-subtle);
    background: var(--pane-bg);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: var(--titlebar-height);
    padding: 0 0.65rem;
    position: relative;
    z-index: 5;
    -webkit-app-region: drag;
    app-region: drag;
  }
  .panel-head :global(button) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .head-actions {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .graph-link {
    border: none;
    background: transparent;
    color: var(--accent-link);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    padding: 0.2rem 0.45rem;
    border-radius: var(--radius-feedback);
    cursor: pointer;
  }

  .graph-link:hover {
    background: var(--chrome-action-hover);
  }


  .title {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .x {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    color: var(--text-faint);
    min-height: 32px;
    min-width: 32px;
    padding: 0.2rem;
    font-size: var(--text-lg);
    border-radius: var(--radius-feedback);
  }

  .x:hover {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .growth {
    font-size: var(--text-sm);
    color: var(--text-faint);
    padding: 0.45rem 0.65rem;
    border-bottom: 1px solid var(--border-subtle);
    line-height: 1.4;
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--border-subtle);
  }

  .tabs button {
    flex: 1;
    background: transparent;
    color: var(--text-faint);
    font-size: var(--text-sm);
    font-weight: var(--font-normal);
    min-height: 32px;
    padding: 0.35rem 0.2rem;
    border-radius: 0;
    border-bottom: 2px solid transparent;
  }

  .tabs button.active {
    color: var(--text);
    border-bottom-color: var(--text-muted);
  }

  .search {
    padding: 0.45rem 0.5rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .body {
    flex: 1;
    min-height: 0;
    padding: 0.4rem 0.35rem 0.75rem;
  }

  .sec {
    font-size: var(--text-xs);
    color: var(--text-faint);
    padding: 0.35rem 0.35rem 0.25rem;
  }

  .list {
    list-style: none;
    margin-bottom: 0.55rem;
  }

  .row {
    width: 100%;
    text-align: left;
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-base);
    font-weight: var(--font-normal);
    padding: 0.4rem 0.35rem;
    border-radius: var(--radius-sm);
    min-height: auto;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
  }

  .row:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .row.on {
    background: var(--accent-live-dim);
    color: var(--text);
  }

  .muted,
  .err {
    font-size: var(--text-sm);
    color: var(--text-faint);
    padding: 0.35rem;
    line-height: 1.45;
  }

  .add {
    margin: 0.35rem;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: var(--text-sm);
    border-radius: var(--radius-sm);
  }

  .tree {
    padding: 0 0.1rem;
  }
</style>
