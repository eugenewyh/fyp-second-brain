<script lang="ts">
  import { assistant } from "$lib/stores/assistant.svelte";
  import {
    emptyAgentStatuses,
    type AgentNodeId,
  } from "$lib/research/agent-graph";
  import AgentGraph from "./AgentGraph.svelte";
  import LiveActivityPanel from "./LiveActivityPanel.svelte";
  import MissionStatusBar from "./MissionStatusBar.svelte";
  import PlanReviewPanel from "./PlanReviewPanel.svelte";

  interface Props {
    onCancel?: () => void;
  }

  let { onCancel }: Props = $props();

  const turn = $derived(assistant.getMissionTurn());
  const statuses = $derived(turn?.agentStatuses ?? emptyAgentStatuses());
  const live = $derived(
    turn?.status === "running" || turn?.status === "awaiting_plan",
  );
  const done = $derived(turn?.status === "done" && !!turn?.result);
</script>

<section class="stage" data-testid="mission-stage">
  {#if !turn}
    <div class="idle">
      <p class="idle-kicker">Mission</p>
      <h1 class="idle-title">Watch the research team work</h1>
      <p class="idle-copy">
        Assign a goal below. Agents plan, retrieve from your library and the web,
        critique themselves, and write lasting knowledge into your vault.
      </p>
    </div>
  {:else}
    <MissionStatusBar
      detail={turn.progressDetail ?? ""}
      runMode={turn.runMode ?? "studio"}
      goalPass={turn.goalPass}
      goalMaxPasses={turn.goalMaxPasses}
      memoryRecalled={turn.memoryRecalled}
      memoryDetail={turn.memoryDetail ?? ""}
      confidence={turn.confidence ?? turn.result?.confidence ?? undefined}
      goalStatus={turn.goalStatus ?? turn.result?.goal_status ?? ""}
      status={turn.status}
    />

    <div class="graph-stage">
      <AgentGraph
        statuses={statuses}
        selected={assistant.selectedAgentNode}
        looping={!!turn.looping}
        detail={turn.progressDetail ?? ""}
        activityLog={turn.activityLog ?? []}
        onSelect={(id: AgentNodeId) => assistant.selectAgentNode(id)}
      />
    </div>

    {#if turn.status === "awaiting_plan"}
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
    {/if}

    <div class="trace-stage">
      <LiveActivityPanel entries={turn.activityLog ?? []} />
    </div>

    <div class="stage-actions">
      {#if live && onCancel}
        <button type="button" class="btn ghost" onclick={onCancel}>Cancel</button>
      {/if}
      {#if done && turn.savedPath}
        <button
          type="button"
          class="btn primary"
          data-testid="open-report"
          onclick={() => assistant.openReportView(turn.id)}
        >
          Open report
        </button>
        <span class="hint">Saved</span>
      {/if}
      {#if turn.status === "error"}
        <button
          type="button"
          class="btn primary"
          data-testid="retry-run"
          disabled={assistant.sessionBusyForTurn(turn.id)}
          onclick={() => void assistant.retryResearch(turn.id)}
        >
          Retry
        </button>
      {/if}
      <button
        type="button"
        class="btn ghost"
        onclick={() => assistant.toggleInspector()}
      >
        {assistant.inspectorOpen ? "Hide details" : "Details"}
      </button>
    </div>
  {/if}
</section>

<style>
  .stage {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    min-height: 0;
    flex: 1;
    padding: 1rem 1.25rem 0.5rem;
    animation: fade-in 0.12s ease-out;
  }

  @keyframes fade-in {
    from {
      opacity: 0.65;
    }
    to {
      opacity: 1;
    }
  }

  .idle {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 2rem 1.5rem 4rem;
    max-width: 28rem;
    margin: 0 auto;
  }

  .idle-kicker {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .idle-title {
    margin: 0.5rem 0 0;
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
    color: var(--text);
  }

  .idle-copy {
    margin: 0.75rem 0 0;
    font-size: var(--text-base);
    line-height: 1.5;
    color: var(--text-muted);
  }

  .graph-stage {
    flex: 0 0 auto;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);
    padding: 0.65rem;
    overflow: hidden;
  }

  .graph-stage :global(.mission) {
    min-height: 200px;
  }

  .interrupt {
    border: 1px solid var(--border-active);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);
    padding: 0.75rem;
    box-shadow: 0 0 0 1px var(--accent-live-dim);
  }

  .trace-stage {
    flex: 1 1 auto;
    min-height: 140px;
    max-height: min(280px, 32vh);
  }

  .stage-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.25rem;
  }

  .btn {
    font-size: var(--text-sm);
    padding: 0.4rem 0.75rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease;
  }

  .btn.primary {
    background: var(--accent-live);
    color: var(--accent-on-live, #ffffff);
    border-color: transparent;
  }

  .btn.primary:hover {
    background: var(--accent-live-hover);
  }

  .btn.ghost {
    background: transparent;
    color: var(--text-muted);
  }

  .btn.ghost:hover {
    color: var(--text);
    background: var(--surface-hover);
  }

  .hint {
    font-size: var(--text-xs);
    color: var(--text-faint);
    font-family: var(--font-mono);
  }
</style>
