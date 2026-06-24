<script lang="ts">
  import { renderReport } from "$lib/research/render";
  import type { ResearchResult } from "$lib/api";

  interface Props {
    query: string;
    connected: boolean;
    loading: boolean;
    result: ResearchResult | null;
    showDetails: boolean;
    onRun: () => void;
    hidden?: boolean;
  }

  let {
    query = $bindable(""),
    connected,
    loading = $bindable(false),
    result = $bindable(null),
    showDetails = $bindable(false),
    onRun,
    hidden = false,
  }: Props = $props();
</script>

<section
  class="panel research-panel"
  class:hidden
  data-testid="research-workspace"
  aria-hidden={hidden}
>
  <h2>Autonomous Research</h2>
  <p class="hint">Multi-agent workflow: planner → retriever → analyst → verifier → synthesizer</p>

  <div class="input-row">
    <textarea
      bind:value={query}
      placeholder="e.g. What are servlets in Java and how do they compare to modern frameworks?"
      rows="3"
      data-testid="research-query"
    ></textarea>
  </div>
  <div class="actions">
    <button
      class="btn-primary"
      onclick={onRun}
      disabled={loading || !connected}
      data-testid="run-research"
    >
      {loading ? "Researching…" : "Run Research"}
    </button>
    {#if result}
      <button class="btn-secondary" onclick={() => (showDetails = !showDetails)}>
        {showDetails ? "Hide details" : "Show details"}
      </button>
    {/if}
  </div>

  {#if loading}
    <div class="loading">Running multi-agent pipeline… This may take 1–2 minutes.</div>
  {/if}

  {#if result && showDetails}
    <div class="details">
      <h3>Plan</h3>
      <pre>{result.plan}</pre>
      <h3>Retrieval</h3>
      <pre>{JSON.stringify(result.retrieval_stats, null, 2)}</pre>
      {#if result.retrieval_log.length}
        <pre>{result.retrieval_log.join("\n")}</pre>
      {/if}
      {#if result.revision_count}
        <p>Revisions: {result.revision_count}</p>
      {/if}
    </div>
  {/if}

  {#if result}
    <div class="report report-content" data-testid="research-report">
      {@html renderReport(result.report)}
    </div>
  {/if}
</section>

<style>
  .research-panel {
    padding: 1.25rem 1.5rem;
    height: 100%;
    overflow-y: auto;
  }

  .research-panel.hidden {
    display: none;
  }

  .research-panel h2 {
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

  .report {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    line-height: 1.6;
    max-height: 60vh;
    overflow-y: auto;
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