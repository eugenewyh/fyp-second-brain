<script lang="ts">
  import type { AssistantTurn } from "$lib/stores/assistant.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import AgentWorkPanel from "./AgentWorkPanel.svelte";
  import ResearchReport from "$lib/components/research/ResearchReport.svelte";
  import FailRetry from "./FailRetry.svelte";
  import { extractOpenQuestions, questionFromGap } from "$lib/research/gaps";

  type ResearchTurn = Extract<AssistantTurn, { kind: "research" }>;

  interface Props {
    turn: ResearchTurn;
    detailsOpen?: boolean;
    onToggleDetails?: () => void;
    onOpenPath?: (path: string) => void;
    onCancel?: () => void;
  }

  let {
    turn,
    detailsOpen = false,
    onToggleDetails,
    onOpenPath,
    onCancel,
  }: Props = $props();

  const live = $derived(turn.status === "running" || turn.status === "awaiting_plan");
  const done = $derived(turn.status === "done" && !!turn.result);
  const failed = $derived(turn.status === "error");

  const showActions = $derived(
    (!!turn.savedPath && !!onOpenPath) ||
      ((done || !!turn.livePlan || (turn.liveQueries?.length ?? 0) > 0) &&
        !!onToggleDetails &&
        !failed),
  );

  const claimCount = $derived(turn.claimCount ?? turn.result?.claim_count ?? 0);
  const remembered = $derived(
    done && (!!turn.indexed || claimCount > 0 || !!turn.memoryDetail),
  );
  const rememberedLabel = $derived(
    claimCount > 0
      ? `${claimCount} claim${claimCount === 1 ? "" : "s"} written back to memory`
      : "Saved to this topic’s memory",
  );
  const deepenGaps = $derived(
    done && turn.result?.report ? extractOpenQuestions(turn.result.report, 3) : [],
  );

  function fillDeepen(gap: string) {
    assistant.input = questionFromGap(gap);
    assistant.composerFocusNonce += 1;
  }
</script>

<article
  class="run"
  class:live
  class:done
  class:err={failed}
  data-testid="agent-run-block"
  data-turn-id={turn.id}
  data-status={turn.status}
>
  {#if live || done || failed}
    <AgentWorkPanel
      {turn}
      {detailsOpen}
      {onToggleDetails}
      {onCancel}
    />
  {/if}

  {#if failed}
    <FailRetry
      error={turn.error}
      disabled={assistant.sessionBusyForTurn(turn.id)}
      detailsOpen={detailsOpen}
      onRetry={() => void assistant.retryResearch(turn.id)}
      onDetails={onToggleDetails}
    />
  {:else if done && turn.result}
    <div class="report">
      <ResearchReport result={turn.result} variant="thread" />
    </div>
  {/if}

  {#if remembered}
    <button
      type="button"
      class="remembered"
      onclick={() => onToggleDetails?.()}
    >
      {rememberedLabel}
    </button>
  {/if}

  {#if showActions && !live}
    <div class="actions">
      {#if turn.savedPath && onOpenPath}
        <button
          type="button"
          class="link"
          data-testid="open-report"
          onclick={() => onOpenPath?.(turn.savedPath!)}
        >
          Open report
        </button>
      {/if}
      {#if (done || turn.livePlan || (turn.liveQueries?.length ?? 0) > 0) && onToggleDetails}
        <button type="button" class="link" onclick={onToggleDetails}>
          {detailsOpen ? "Hide details" : "Details"}
        </button>
      {/if}
    </div>
  {/if}

  {#if deepenGaps.length}
    <div class="deepen" role="group" aria-label="Deepen">
      {#each deepenGaps as gap}
        <button type="button" class="chip" onclick={() => fillDeepen(gap)}>
          {gap}
        </button>
      {/each}
    </div>
  {/if}
</article>

<style>
  .run {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    width: 100%;
  }

  .report {
    min-width: 0;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 0.85rem;
    align-items: center;
  }

  .link {
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 0;
  }

  .link:hover {
    color: var(--text);
    text-decoration: underline;
  }

  .remembered {
    align-self: flex-start;
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-faint);
    cursor: pointer;
    border-radius: 0;
  }

  .remembered:hover {
    color: var(--text-muted);
    text-decoration: underline;
  }

  .deepen {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .chip {
    max-width: 100%;
    text-align: left;
    font-size: var(--text-sm);
    color: var(--text-muted);
    background: var(--control-fill);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 0.38rem 0.75rem;
    line-height: 1.4;
    cursor: pointer;
    transition:
      background var(--dur-control, 0.1s) var(--ease-out, ease),
      color var(--dur-control, 0.1s) var(--ease-out, ease),
      border-color var(--dur-control, 0.1s) var(--ease-out, ease);
  }

  .chip:hover {
    color: var(--text);
    background: var(--surface-hover);
    border-color: var(--border-active);
  }
</style>
