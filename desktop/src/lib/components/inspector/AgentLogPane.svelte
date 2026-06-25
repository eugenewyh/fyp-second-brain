<script lang="ts">
  import { research } from "$lib/stores/research.svelte";
</script>

<div class="agent-log">
  {#if research.loading}
    <p class="loading">Pipeline running…</p>
  {:else if research.result}
    <div class="section">
      <h4>Revisions</h4>
      <p>{research.result.revision_count}</p>
    </div>
    <div class="section">
      <h4>Retrieval stats</h4>
      <pre>{JSON.stringify(research.result.retrieval_stats, null, 2)}</pre>
    </div>
    {#if research.result.retrieval_log.length}
      <div class="section">
        <h4>Retrieval log</h4>
        <pre>{research.result.retrieval_log.join("\n")}</pre>
      </div>
    {/if}
    <div class="section">
      <h4>Verifier / self-critique</h4>
      <p class="hint">Revision count reflects verifier feedback loops (max 2).</p>
      {#if research.result.analysis}
        <pre>{research.result.analysis.slice(0, 1500)}{research.result.analysis.length > 1500 ? "…" : ""}</pre>
      {/if}
    </div>
  {:else}
    <p class="empty">Run research to see agent process log</p>
  {/if}
</div>

<style>
  .agent-log {
    padding: 0.75rem;
    font-size: 0.8rem;
    overflow-y: auto;
    height: 100%;
  }

  .section {
    margin-bottom: 1rem;
  }

  .section h4 {
    font-size: 0.75rem;
    color: var(--accent);
    margin-bottom: 0.35rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  pre {
    white-space: pre-wrap;
    color: var(--text-muted);
    font-size: 0.75rem;
    background: var(--bg);
    padding: 0.5rem;
    border-radius: 6px;
    border: 1px solid var(--border);
  }

  .loading {
    color: var(--warning);
  }

  .empty,
  .hint {
    color: var(--text-muted);
    font-size: 0.75rem;
  }
</style>