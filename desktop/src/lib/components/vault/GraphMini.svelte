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
  import SectionLabel from "$lib/ui/SectionLabel.svelte";
  import Button from "$lib/ui/Button.svelte";

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
  <SectionLabel>Recent</SectionLabel>
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

  <div class="section-gap"><SectionLabel>Suggested</SectionLabel></div>
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

  <Button variant="ghost" onclick={() => (graphExpanded = !graphExpanded)}>
    {graphExpanded ? "Hide graph" : "Show graph"}
  </Button>
  {#if graphExpanded && graphData.nodes.length}
    <KnowledgeGraph data={graphData} />
  {/if}
</div>

<style>
  .graph-mini {
    padding: 0.5rem 0.65rem;
    border-top: 1px solid var(--border-subtle);
    font-size: 0.75rem;
  }

  .section-gap {
    margin-top: 0.65rem;
    margin-bottom: 0.35rem;
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
    color: var(--text-faint);
    font-size: 0.65rem;
    margin-bottom: 0.25rem;
  }
</style>