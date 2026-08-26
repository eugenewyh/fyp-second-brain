<script lang="ts">
  import { onMount } from "svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { resolveSourcePath } from "$lib/vault/source-path";
  import { loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import { flattenVaultFiles } from "$lib/vault/flatten";

  let vaultFiles = $state<{ path: string; name: string }[]>([]);

  const researchResult = $derived.by(() => {
    const thread = assistant.getActiveThread();
    for (let i = thread.length - 1; i >= 0; i -= 1) {
      const turn = thread[i];
      if (turn.kind === "research" && turn.result) return turn.result;
    }
    return null;
  });

  onMount(async () => {
    const root = workspace.vaultRoot ?? (await getVaultRoot());
    workspace.vaultRoot = root;
    const tree = await loadVaultTree(root);
    vaultFiles = flattenVaultFiles(tree);
  });

  function openSource(source: string, page: number | null) {
    const path = resolveSourcePath(source, workspace.vaultRoot, vaultFiles);
    if (!path) return;
    tabs.openNoteTab(path);
    workspace.setActiveNote(path);
    if (path.endsWith(".pdf") && page) {
      workspace.pdfJumpPage = page;
    }
  }
</script>

<div class="sources" data-testid="sources-section">
  {#if researchResult}
    <h4>Research sources</h4>
    <div class="section">
      <p class="label">Search queries used</p>
      <ul>
        {#each researchResult.retrieval_queries as q}
          <li>{q}</li>
        {/each}
      </ul>
    </div>
    <div class="section">
      <p class="label">Sources found</p>
      <ul class="stats-list">
        {#each Object.entries(researchResult.retrieval_stats) as [key, count]}
          <li><span class="key">{key}</span> {count}</li>
        {/each}
      </ul>
    </div>
  {:else if assistant.lastSources.length}
    <h4>Answer sources</h4>
    <ul>
      {#each assistant.lastSources as src}
        <li>
          <button class="source-btn" onclick={() => openSource(src.source, src.page)}>
            <strong>[{src.index}]</strong> {src.source}
            {#if src.page}<span>, p.{src.page}</span>{/if}
          </button>
          <p class="excerpt">{src.excerpt?.slice(0, 100)}</p>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="hint">Sources appear after you research or get a quick answer</p>
  {/if}
</div>

<style>
  .sources {
    padding: 0.75rem;
    font-size: var(--text-sm);
    overflow-y: auto;
    height: 100%;
  }

  h4 {
    font-size: var(--text-sm);
    color: var(--accent);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
  }

  .section {
    margin-bottom: 0.75rem;
  }

  .label {
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  ul {
    list-style: none;
    padding-left: 0;
  }

  li {
    margin-bottom: 0.5rem;
    font-size: var(--text-sm);
  }

  .stats-list .key {
    text-transform: capitalize;
    color: var(--text-muted);
  }

  .excerpt {
    color: var(--text-muted);
    font-size: var(--text-xs);
    margin-top: 0.15rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: var(--text-sm);
  }

  .source-btn {
    background: transparent;
    color: var(--text);
    padding: 0;
    font-size: inherit;
    text-align: left;
  }

  .source-btn:hover {
    color: var(--accent);
  }
</style>