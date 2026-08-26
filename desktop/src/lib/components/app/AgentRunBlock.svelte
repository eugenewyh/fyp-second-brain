<script lang="ts">
  import type { AssistantTurn } from "$lib/stores/assistant.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import PlanReviewPanel from "$lib/components/mission/PlanReviewPanel.svelte";
  import ResearchReport from "$lib/components/research/ResearchReport.svelte";
  import FailRetry from "./FailRetry.svelte";
  import { extractOpenQuestions, questionFromGap } from "$lib/research/gaps";
  import { readableStatusLines } from "$lib/research/status-copy";

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

  const allLines = $derived(readableStatusLines(turn.activityLog));
  /** Keep the live transcript scannable — show recent lines, dim older ones. */
  const MAX_VISIBLE = 5;
  const liveLines = $derived(
    allLines.length > MAX_VISIBLE ? allLines.slice(-MAX_VISIBLE) : allLines,
  );
  const hiddenCount = $derived(
    allLines.length > MAX_VISIBLE ? allLines.length - MAX_VISIBLE : 0,
  );
  const live = $derived(turn.status === "running" || turn.status === "awaiting_plan");
  const done = $derived(turn.status === "done" && !!turn.result);
  const failed = $derived(turn.status === "error");
  const passLabel = $derived(
    turn.runMode === "goal" && turn.goalPass && turn.goalMaxPasses
      ? `Pass ${turn.goalPass}/${turn.goalMaxPasses}`
      : "",
  );
  const stateLabel = $derived(
    live
      ? turn.status === "awaiting_plan"
        ? "Needs review"
        : "Working"
      : failed
        ? "Failed"
        : done
          ? "Done"
          : "",
  );
  const thoughtLabel = $derived(
    [stateLabel, passLabel].filter(Boolean).join(" · "),
  );
  const showActions = $derived(
    (live && !!onCancel) ||
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
      ? `Saved ${claimCount} idea${claimCount === 1 ? "" : "s"} from this chat`
      : "Saved to this chat",
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
  {#if turn.status === "awaiting_plan"}
    {#if thoughtLabel}
      <p class="thought live-thought">
        <span class="pulse" aria-hidden="true"></span>
        {thoughtLabel}
      </p>
    {/if}
    <div class="interrupt">
      <PlanReviewPanel
        plan={turn.livePlan ?? ""}
        queries={turn.liveQueries ?? []}
        expiresAt={turn.planExpiresAt}
        busy={assistant.sessionBusyForTurn(turn.id)}
        retrievalScope={turn.retrievalScope ?? assistant.retrievalScope}
        onApprove={(edits) => void assistant.approvePlan(turn.id, edits)}
        onRegenerate={() => void assistant.regeneratePlan(turn.id)}
        onCancel={() => void assistant.cancelPlanReview(turn.id)}
        onSkipAuto={() =>
          void assistant.runResearch(null, turn.query, {
            skipPlanReview: true,
            continuePrior: !!turn.priorContext,
          })}
      />
    </div>
  {:else if live}
    {#if thoughtLabel}
      <p class="thought live-thought">
        <span class="pulse" aria-hidden="true"></span>
        {thoughtLabel}
      </p>
    {/if}
    <ul class="status-lines" aria-live="polite">
      {#if hiddenCount > 0}
        <li class="line muted-more">
          <span class="line-mark" aria-hidden="true"></span>
          <span class="line-text">{hiddenCount} earlier step{hiddenCount === 1 ? "" : "s"}</span>
        </li>
      {/if}
      {#each liveLines as line, i (line.id)}
        <li
          class="line"
          class:is-latest={i === liveLines.length - 1}
          class:is-prior={i < liveLines.length - 1}
          data-tone={line.tone}
        >
          <span class="line-mark" aria-hidden="true"></span>
          <span class="line-text">{line.text}</span>
        </li>
      {:else}
        <li class="line is-latest" data-tone="live">
          <span class="line-mark" aria-hidden="true"></span>
          <span class="line-text">Starting…</span>
        </li>
      {/each}
    </ul>
  {:else}
    {#if thoughtLabel}
      <details class="thought-details">
        <summary class="thought" class:ok={done} class:bad={failed}>
          {thoughtLabel}
        </summary>
        <ul class="status-lines">
          {#each allLines as line, i (line.id)}
            <li
              class="line"
              class:is-latest={i === allLines.length - 1}
              class:is-prior={i < allLines.length - 1}
              data-tone={line.tone}
            >
              <span class="line-mark" aria-hidden="true"></span>
              <span class="line-text">{line.text}</span>
            </li>
          {:else}
            <li class="line muted-more">
              <span class="line-mark" aria-hidden="true"></span>
              <span class="line-text">No steps recorded</span>
            </li>
          {/each}
        </ul>
      </details>
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
  {/if}

  {#if showActions}
    <div class="actions">
      {#if live && onCancel}
        <button type="button" class="link" onclick={onCancel}>Cancel</button>
      {/if}
      {#if turn.savedPath && onOpenPath}
        <button type="button" class="link" data-testid="open-report" onclick={() => onOpenPath?.(turn.savedPath!)}>
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

  .thought {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.45;
  }

  .thought.ok {
    color: var(--text-muted);
  }

  .thought.bad {
    color: var(--error);
  }

  .live-thought {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--text-muted);
  }

  .pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-live);
    flex-shrink: 0;
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.35;
    }
  }

  .thought-details {
    margin: 0;
  }

  .thought-details summary {
    cursor: pointer;
    list-style: none;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    user-select: none;
  }

  .thought-details summary::-webkit-details-marker {
    display: none;
  }

  .thought-details summary::before {
    content: "";
    width: 0;
    height: 0;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
    border-left: 5px solid color-mix(in srgb, var(--text) 38%, transparent);
    flex-shrink: 0;
    transition: transform var(--dur-control, 0.1s) var(--ease-out, ease);
  }

  .thought-details[open] summary::before {
    transform: rotate(90deg);
  }

  .thought-details[open] .status-lines {
    margin-top: 0.45rem;
  }

  .status-lines {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.28rem;
  }

  .line {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.5;
  }

  .line.is-prior {
    color: var(--text-faint);
  }

  .line.is-latest {
    color: var(--text);
    font-size: var(--text-base);
  }

  .line.muted-more {
    color: var(--text-faint);
    font-size: var(--text-xs);
  }

  .line.muted-more .line-mark {
    background: transparent;
    border: 1px solid color-mix(in srgb, var(--text) 22%, transparent);
  }

  .line-mark {
    width: 5px;
    height: 5px;
    margin-top: 0.42rem;
    border-radius: 50%;
    background: color-mix(in srgb, var(--text) 22%, transparent);
    flex-shrink: 0;
  }

  .line-text {
    min-width: 0;
  }

  .line[data-tone="live"] .line-mark {
    background: var(--accent-live);
  }

  .line[data-tone="success"] .line-mark {
    background: var(--success);
  }

  .line[data-tone="warning"] {
    color: var(--warning);
  }

  .line[data-tone="warning"] .line-mark {
    background: var(--warning);
  }

  .line[data-tone="error"] {
    color: var(--error);
  }

  .line[data-tone="error"] .line-mark {
    background: var(--error);
  }

  .interrupt {
    margin: 0.1rem 0;
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
