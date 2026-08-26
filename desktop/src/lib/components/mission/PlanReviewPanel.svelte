<script lang="ts">
  import Button from "$lib/ui/Button.svelte";
  import SectionHeader from "$lib/ui/SectionHeader.svelte";
  import Badge from "$lib/ui/Badge.svelte";

  interface Props {
    plan: string;
    queries: string[];
    expiresAt?: string;
    busy?: boolean;
    retrievalScope?: string;
    onApprove: (edits: { plan: string; retrieval_queries: string[] }) => void;
    onRegenerate: () => void;
    onCancel: () => void;
    onSkipAuto?: () => void;
  }

  let {
    plan,
    queries,
    expiresAt = "",
    busy = false,
    retrievalScope = "hybrid",
    onApprove,
    onRegenerate,
    onCancel,
    onSkipAuto,
  }: Props = $props();

  let editPlan = $state("");
  let editQueries = $state("");

  $effect(() => {
    editPlan = plan;
    editQueries = queries.join("\n");
  });

  function approve() {
    const qs = editQueries
      .split("\n")
      .map((q) => q.trim())
      .filter(Boolean);
    onApprove({ plan: editPlan.trim(), retrieval_queries: qs });
  }
</script>

<section class="plan-review" data-testid="plan-review-panel">
  <SectionHeader title="Plan review" subtitle="Edit then approve — HITL before retrieval" mono />

  <div class="meta">
    <Badge variant="live">awaiting approval</Badge>
    <Badge variant="default">scope: {retrievalScope}</Badge>
    {#if expiresAt}
      <span class="exp">expires {expiresAt.slice(0, 19).replace("T", " ")} UTC</span>
    {/if}
  </div>

  <label class="field">
    <span class="lbl">Research plan</span>
    <textarea class="ta" rows="6" bind:value={editPlan} disabled={busy}></textarea>
  </label>

  <label class="field">
    <span class="lbl">Search queries (one per line, keep [personal]/[web]/[arxiv] tags)</span>
    <textarea class="ta mono" rows="5" bind:value={editQueries} disabled={busy}></textarea>
  </label>

  <div class="actions">
    <Button variant="live" disabled={busy || !editPlan.trim()} onclick={approve}>
      {busy ? "Working…" : "Approve & execute"}
    </Button>
    <Button variant="secondary" disabled={busy} onclick={onRegenerate}>Regenerate</Button>
    <Button variant="ghost" disabled={busy} onclick={onCancel}>Cancel</Button>
    {#if onSkipAuto}
      <Button variant="ghost" disabled={busy} onclick={onSkipAuto}>Run auto (skip review)</Button>
    {/if}
  </div>
</section>

<style>
  .plan-review {
    background: var(--bg-elevated);
    border: 1px solid var(--border-active);
    border-radius: var(--radius-md);
    padding: var(--space-4);
  }

  .meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .exp {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
  }

  .lbl {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
  }

  .ta {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text);
    font-size: var(--text-sm);
    padding: 0.55rem 0.65rem;
    line-height: 1.45;
    resize: vertical;
    min-height: 4rem;
  }

  .ta.mono {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
  }

  .ta:focus {
    outline: 1px solid var(--focus-ring);
    border-color: var(--border-active);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
</style>
