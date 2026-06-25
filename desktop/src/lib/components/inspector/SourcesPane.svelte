<script lang="ts">
  import { research } from "$lib/stores/research.svelte";
</script>

<div class="sources">
  {#if research.result}
    <h4>Research sources</h4>
    <div class="section">
      <p class="label">Retrieval queries</p>
      <ul>
        {#each research.result.retrieval_queries as q}
          <li>{q}</li>
        {/each}
      </ul>
    </div>
    <div class="section">
      <p class="label">Stats</p>
      <pre>{JSON.stringify(research.result.retrieval_stats, null, 2)}</pre>
    </div>
  {:else if research.quickResult?.sources.length}
    <h4>Query sources</h4>
    <ul>
      {#each research.quickResult.sources as src}
        <li>
          <strong>[{src.index}]</strong> {src.source}
          {#if src.page}<span>, p.{src.page}</span>{/if}
          <p class="excerpt">{src.excerpt?.slice(0, 100)}</p>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="hint">Sources appear after research or quick query</p>
  {/if}
</div>

<style>
  .sources {
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
  }

  .section {
    margin-bottom: 0.75rem;
  }

  .label {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  ul {
    list-style: none;
    padding-left: 0;
  }

  li {
    margin-bottom: 0.5rem;
    font-size: 0.75rem;
  }

  pre {
    font-size: 0.7rem;
    white-space: pre-wrap;
    color: var(--text-muted);
  }

  .excerpt {
    color: var(--text-muted);
    font-size: 0.7rem;
    margin-top: 0.15rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.75rem;
  }
</style>