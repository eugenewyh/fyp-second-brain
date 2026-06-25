<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { api, type VaultSearchResult } from "$lib/api";
  import { loadVaultTree, readNote, getVaultRoot } from "$lib/vault/load";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import { splitFrontmatter } from "$lib/vault/markdown";
  import { buildBacklinkIndex } from "$lib/vault/backlinks";
  import { mergeSuggestions, type SuggestionItem } from "$lib/vault/suggestions";
  import { buildGraphData } from "$lib/vault/graph-data";
  import KnowledgeGraph from "./KnowledgeGraph.svelte";

  let suggestions = $state<SuggestionItem[]>([]);
  let graphExpanded = $state(false);
  let graphData = $state(buildGraphData(null, { byTarget: new Map() }, {}, []));
  let bodies = $state<Record<string, string>>({});
  let vaultFiles = $state<{ path: string; name: string }[]>([]);

  function openPath(path: string) {
    tabs.openNoteTab(path);
    workspace.setActiveNote(path);
  }

  async function refreshConnections() {
    if (!workspace.activeNotePath) {
      suggestions = [];
      graphData = buildGraphData(null, { byTarget: new Map() }, {}, []);
      return;
    }

    const root = workspace.vaultRoot ?? (await getVaultRoot());
    workspace.vaultRoot = root;
    const tree = await loadVaultTree(root);
    vaultFiles = flattenVaultFiles(tree);

    const mdFiles = vaultFiles.filter((f) => f.path.endsWith(".md"));
    const loaded: Record<string, string> = {};
    await Promise.all(
      mdFiles.map(async (f) => {
        try {
          const raw = await readNote(f.path);
          loaded[f.path] = splitFrontmatter(raw).body;
        } catch {
          /* skip unreadable */
        }
      }),
    );
    bodies = loaded;

    const index = buildBacklinkIndex(vaultFiles, loaded);
    let embeddingHits: VaultSearchResult[] = [];
    if (connection.connected) {
      try {
        const name = workspace.activeNotePath.split("/").pop() ?? "";
        const excerpt = loaded[workspace.activeNotePath]?.slice(0, 500) ?? name;
        const result = await api.vaultRelated(excerpt || name, 5);
        embeddingHits = result.results;
      } catch {
        embeddingHits = [];
      }
    }

    suggestions = mergeSuggestions(
      workspace.activeNotePath,
      index,
      embeddingHits,
      vaultFiles,
    );

    const embeddingPaths = embeddingHits
      .map((h) => vaultFiles.find((f) => f.name === (h.source.split("/").pop() ?? h.source))?.path)
      .filter((p): p is string => Boolean(p))
      .slice(0, 3);

    graphData = buildGraphData(
      workspace.activeNotePath,
      index,
      loaded,
      vaultFiles,
      embeddingPaths,
    );
  }

  $effect(() => {
    workspace.activeNotePath;
    workspace.vaultRefreshNonce;
    void refreshConnections();
  });
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
  {#if suggestions.length}
    <ul>
      {#each suggestions as item}
        <li>
          <button onclick={() => openPath(item.path)}>
            <span class="kind">{item.kind === "backlink" ? "←" : "~"}</span>
            {item.label}
          </button>
          {#if item.excerpt}
            <p class="excerpt">{item.excerpt.slice(0, 80)}…</p>
          {/if}
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty">Open a note for backlinks & related chunks</p>
  {/if}

  <button class="graph-toggle" onclick={() => (graphExpanded = !graphExpanded)}>
    {graphExpanded ? "Hide graph" : "Show graph"}
  </button>
  {#if graphExpanded && graphData.nodes.length}
    <KnowledgeGraph data={graphData} />
  {/if}
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

  .kind {
    color: var(--accent);
    margin-right: 0.25rem;
  }

  .excerpt {
    font-size: 0.65rem;
    color: var(--text-muted);
    padding-left: 0.4rem;
    margin-bottom: 0.25rem;
  }

  .empty {
    color: var(--text-muted);
    font-size: 0.7rem;
  }

  .graph-toggle {
    margin-top: 0.5rem;
    font-size: 0.7rem;
    color: var(--accent);
    background: transparent;
    padding: 0.2rem 0;
  }
</style>