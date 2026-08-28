<script lang="ts">
  import type { AssistantTurn } from "$lib/stores/assistant.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import PlanReviewPanel from "$lib/components/mission/PlanReviewPanel.svelte";
  import { formatWorkedDuration } from "$lib/assistant/elapsed";
  import { readableStatusLines } from "$lib/research/status-copy";
  import { ChevronRight } from "@lucide/svelte";

  type ResearchTurn = Extract<AssistantTurn, { kind: "research" }>;

  interface Props {
    turn: ResearchTurn;
    detailsOpen?: boolean;
    onToggleDetails?: () => void;
    onCancel?: () => void;
  }

  let {
    turn,
    detailsOpen = false,
    onToggleDetails,
    onCancel,
  }: Props = $props();

  let logExpanded = $state(false);
  let expanded = $state(true);

  const allLines = $derived(readableStatusLines(turn.activityLog));
  const latestLine = $derived(allLines.at(-1));
  const priorLines = $derived(allLines.length > 1 ? allLines.slice(0, -1) : []);
  const MAX_PRIOR = 3;
  const hiddenPrior = $derived(
    priorLines.length > MAX_PRIOR ? priorLines.length - MAX_PRIOR : 0,
  );
  const visiblePrior = $derived(
    logExpanded || hiddenPrior === 0 ? priorLines : priorLines.slice(-MAX_PRIOR),
  );

  const live = $derived(turn.status === "running" || turn.status === "awaiting_plan");
  const done = $derived(turn.status === "done");
  const failed = $derived(turn.status === "error");

  const passLabel = $derived(
    turn.runMode === "goal" && turn.goalPass && turn.goalMaxPasses
      ? `Pass ${turn.goalPass}/${turn.goalMaxPasses}`
      : "",
  );

  const liveLabel = $derived(
    turn.status === "awaiting_plan" ? "Needs review" : "Researching",
  );

  const summaryLabel = $derived(
    live
      ? [liveLabel, passLabel].filter(Boolean).join(" · ")
      : failed
        ? "Failed"
        : done && turn.runStartedAt
          ? `Worked for ${formatWorkedDuration(Date.now() - turn.runStartedAt)}`
          : done
            ? "Report ready"
            : "",
  );

  const currentStep = $derived(
    latestLine?.text ?? (live && allLines.length === 0 ? "Starting…" : ""),
  );

  const shimmer = $derived(live && turn.status === "running");

  $effect(() => {
    void turn.id;
    void turn.status;
    logExpanded = false;
    expanded = live;
  });

  function toggleExpanded() {
    expanded = !expanded;
  }
</script>

<section
  class="work-panel"
  class:is-live={live}
  class:is-done={done}
  class:is-failed={failed}
  aria-busy={live ? true : undefined}
  aria-live={live ? "polite" : undefined}
  data-testid="agent-work-panel"
>
  {#if summaryLabel}
    <button
      type="button"
      class="summary"
      aria-expanded={expanded}
      onclick={toggleExpanded}
    >
      <span class="chevron" class:open={expanded} aria-hidden="true">
        <ChevronRight size={12} strokeWidth={2} />
      </span>
      <span class="summary-label" class:shimmer={shimmer}>{summaryLabel}</span>
    </button>
  {/if}

  {#if expanded}
    <div class="body">
      {#if turn.status === "awaiting_plan"}
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
      {:else if live}
        {#if currentStep}
          <p class="current-step">{currentStep}</p>
        {/if}
        {#if priorLines.length > 0}
          <div class="prior-log">
            {#if hiddenPrior > 0 && !logExpanded}
              <button
                type="button"
                class="log-more"
                onclick={() => (logExpanded = true)}
              >
                {hiddenPrior} earlier step{hiddenPrior === 1 ? "" : "s"}
              </button>
            {/if}
            <ul class="log-lines">
              {#each visiblePrior as line (line.id)}
                <li class="log-line" data-tone={line.tone}>
                  <span class="log-mark" aria-hidden="true"></span>
                  <span class="log-text">{line.text}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      {:else if allLines.length > 0}
        <ul class="log-lines full">
          {#each allLines as line, i (line.id)}
            <li
              class="log-line"
              class:is-latest={i === allLines.length - 1}
              data-tone={line.tone}
            >
              <span class="log-mark" aria-hidden="true"></span>
              <span class="log-text">{line.text}</span>
            </li>
          {/each}
        </ul>
      {:else if done || failed}
        <p class="empty-log">No steps recorded</p>
      {/if}
    </div>
  {/if}

  {#if live && (onCancel || onToggleDetails)}
    <footer class="foot">
      {#if onCancel}
        <button type="button" class="foot-link" onclick={onCancel}>
          {turn.status === "awaiting_plan" ? "Cancel run" : "Cancel"}
        </button>
      {/if}
      {#if onToggleDetails && (turn.livePlan || (turn.liveQueries?.length ?? 0) > 0)}
        <button type="button" class="foot-link" onclick={onToggleDetails}>
          {detailsOpen ? "Hide details" : "Details"}
        </button>
      {/if}
    </footer>
  {/if}
</section>

<style>
  .work-panel {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    width: 100%;
    min-width: 0;
  }

  .summary {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin: 0;
    padding: 0;
    border: none;
    background: none;
    cursor: pointer;
    min-height: auto;
    text-align: left;
    max-width: 100%;
  }

  .summary:hover .summary-label {
    color: var(--text);
  }

  .chevron {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    color: var(--text-faint);
    flex-shrink: 0;
    transition: transform var(--dur-control, 0.1s) var(--ease-out, ease);
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .summary-label {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    line-height: 1.45;
    color: var(--text-muted);
  }

  .summary-label.shimmer {
    background: linear-gradient(
      90deg,
      var(--text-muted) 0%,
      var(--text) 45%,
      var(--text-muted) 90%
    );
    background-size: 200% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: label-shimmer 2.2s ease-in-out infinite;
  }

  @keyframes label-shimmer {
    0% {
      background-position: 100% center;
    }
    100% {
      background-position: -100% center;
    }
  }

  .body {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    padding-left: calc(14px + 0.35rem);
    min-width: 0;
  }

  .current-step {
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.45;
    color: var(--text-muted);
  }

  .prior-log {
    display: flex;
    flex-direction: column;
    gap: 0.28rem;
  }

  .log-more {
    align-self: flex-start;
    margin: 0;
    padding: 0;
    border: none;
    background: none;
    font-size: var(--text-xs);
    color: var(--text-faint);
    cursor: pointer;
    min-height: auto;
    line-height: 1.4;
  }

  .log-more:hover {
    color: var(--text-muted);
    text-decoration: underline;
  }

  .log-lines {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.22rem;
  }

  .log-line {
    display: flex;
    align-items: flex-start;
    gap: 0.45rem;
    font-size: var(--text-xs);
    line-height: 1.45;
    color: var(--text-faint);
  }

  .log-lines.full .log-line {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .log-lines.full .log-line.is-latest {
    color: var(--text);
  }

  .log-mark {
    width: 4px;
    height: 4px;
    margin-top: 0.38rem;
    border-radius: 50%;
    background: color-mix(in srgb, var(--text) 18%, transparent);
    flex-shrink: 0;
  }

  .log-line[data-tone="success"] .log-mark {
    background: color-mix(in srgb, var(--success) 55%, transparent);
  }

  .log-line[data-tone="live"] .log-mark {
    background: color-mix(in srgb, var(--accent-live) 55%, transparent);
  }

  .log-text {
    min-width: 0;
  }

  .empty-log {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .foot {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 0.85rem;
    align-items: center;
    padding-left: calc(14px + 0.35rem);
  }

  .foot-link {
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-faint);
    cursor: pointer;
    border-radius: 0;
  }

  .foot-link:hover {
    color: var(--text-muted);
    text-decoration: underline;
  }

  @media (prefers-reduced-motion: reduce) {
    .summary-label.shimmer {
      animation: none;
      background: none;
      -webkit-background-clip: unset;
      background-clip: unset;
      color: var(--text-muted);
    }

    .chevron {
      transition: none;
    }
  }
</style>
