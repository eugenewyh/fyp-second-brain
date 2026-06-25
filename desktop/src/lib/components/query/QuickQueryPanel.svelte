<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
</script>

<section class="panel">
  <h2>Quick Query</h2>
  <p class="hint">Fast RAG lookup against your personal knowledge base</p>

  <div class="input-row">
    <input bind:value={research.quickQuestion} placeholder="Ask a question…" />
  </div>
  <button
    class="btn-primary"
    onclick={() => research.runQuickQuery()}
    disabled={research.quickLoading || !connection.connected}
  >
    {research.quickLoading ? "Searching…" : "Ask"}
  </button>

  {#if research.quickResult}
    <div class="answer-box">
      <h3>Answer</h3>
      <p>{research.quickResult.answer}</p>
      {#if research.quickResult.sources.length}
        <h3>Sources</h3>
        <ul>
          {#each research.quickResult.sources as src}
            <li>[{src.index}] {src.source}{src.page ? `, p.${src.page}` : ""}</li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</section>

<style>
  .panel h2 {
    font-size: 1.4rem;
    margin-bottom: 0.25rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 1.25rem;
  }

  .input-row {
    margin-bottom: 0.75rem;
  }

  .answer-box {
    margin-top: 1.25rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
  }

  .answer-box h3 {
    font-size: 0.9rem;
    color: var(--accent);
    margin-bottom: 0.5rem;
  }

  .answer-box ul {
    margin-top: 0.5rem;
    padding-left: 1.2rem;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
</style>