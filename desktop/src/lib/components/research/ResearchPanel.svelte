<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
  import ResearchReport from "./ResearchReport.svelte";
  import Panel from "$lib/ui/Panel.svelte";
  import Button from "$lib/ui/Button.svelte";
</script>

<Panel title="Research" description="Multi-agent workflow with citations">
  {#snippet actions()}
    {#if research.result}
      <Button variant="ghost" onclick={() => (research.showDetails = !research.showDetails)}>
        {research.showDetails ? "Hide details" : "Details"}
      </Button>
    {/if}
  {/snippet}

  <textarea
    bind:value={research.query}
    placeholder="What should I research?"
    rows="3"
  ></textarea>

  <div class="actions">
    <Button
      variant="primary"
      onclick={() => research.runResearch()}
      disabled={research.loading || !connection.connected}
    >
      {research.loading ? "Running…" : "Run research"}
    </Button>
  </div>

  {#if research.loading}
    <div class="loading">Pipeline running — may take 1–2 minutes</div>
  {/if}

  {#if research.result && research.showDetails}
    <div class="details">
      <h3>Plan</h3>
      <pre>{research.result.plan}</pre>
      <h3>Retrieval</h3>
      <pre>{JSON.stringify(research.result.retrieval_stats, null, 2)}</pre>
    </div>
  {/if}

  {#if research.result}
    <ResearchReport result={research.result} />
  {/if}
</Panel>

<style>
  textarea {
    margin-bottom: 0.65rem;
  }

  .actions {
    margin-bottom: 1rem;
  }

  .loading {
    color: var(--text-faint);
    font-size: 0.75rem;
    padding: 0.65rem 0;
    margin-bottom: 0.5rem;
  }

  .details {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
  }

  .details h3 {
    font-size: 0.7rem;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0.5rem 0 0.25rem;
  }

  .details h3:first-child {
    margin-top: 0;
  }

  .details pre {
    color: var(--text-muted);
    white-space: pre-wrap;
    font-family: var(--font-mono);
    font-size: 0.65rem;
  }
</style>