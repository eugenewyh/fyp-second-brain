<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
  import ResearchReport from "./ResearchReport.svelte";
</script>

<section class="panel">
  <h2>Autonomous Research</h2>
  <p class="hint">Multi-agent workflow: planner → retriever → analyst → verifier → synthesizer</p>

  <div class="input-row">
    <textarea
      bind:value={research.query}
      placeholder="e.g. What are servlets in Java and how do they compare to modern frameworks?"
      rows="3"
    ></textarea>
  </div>
  <div class="actions">
    <button
      class="btn-primary"
      onclick={() => research.runResearch()}
      disabled={research.loading || !connection.connected}
    >
      {research.loading ? "Researching…" : "Run Research"}
    </button>
    {#if research.result}
      <button class="btn-secondary" onclick={() => (research.showDetails = !research.showDetails)}>
        {research.showDetails ? "Hide details" : "Show details"}
      </button>
    {/if}
  </div>

  {#if research.loading}
    <div class="loading">Running multi-agent pipeline… This may take 1–2 minutes.</div>
  {/if}

  {#if research.result && research.showDetails}
    <div class="details">
      <h3>Plan</h3>
      <pre>{research.result.plan}</pre>
      <h3>Retrieval</h3>
      <pre>{JSON.stringify(research.result.retrieval_stats, null, 2)}</pre>
      {#if research.result.retrieval_log.length}
        <pre>{research.result.retrieval_log.join("\n")}</pre>
      {/if}
      {#if research.result.revision_count}
        <p>Revisions: {research.result.revision_count}</p>
      {/if}
    </div>
  {/if}

  {#if research.result}
    <ResearchReport result={research.result} />
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

  .actions {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
  }

  .loading {
    color: var(--warning);
    padding: 1rem;
    background: var(--surface);
    border-radius: var(--radius);
    margin-bottom: 1rem;
  }

  .details {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-bottom: 1rem;
    font-size: 0.8rem;
  }

  .details pre {
    white-space: pre-wrap;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
  }

  .details h3 {
    font-size: 0.85rem;
    color: var(--accent);
    margin-bottom: 0.3rem;
  }
</style>