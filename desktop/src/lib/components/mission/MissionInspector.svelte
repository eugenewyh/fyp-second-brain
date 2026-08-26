<script lang="ts">
  import { assistant } from "$lib/stores/assistant.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import SectionHeader from "$lib/ui/SectionHeader.svelte";
  import SelfCritiquePanel from "./SelfCritiquePanel.svelte";
  import RunSummary from "./RunSummary.svelte";

  const turn = $derived(assistant.getMissionTurn());

  const critiqueHistory = $derived(
    turn?.liveCritiqueHistory?.length
      ? turn.liveCritiqueHistory
      : (turn?.result?.critique_history ?? []),
  );

  const done = $derived(turn?.status === "done" && !!turn?.result);

  function openPath(path: string) {
    app.openDocument(path, { from: "agent" });
    workspace.setActiveNote(path);
  }
</script>

{#if turn}
  <aside class="inspector ui-scroll" data-testid="mission-inspector" aria-label="Mission details">
    <div class="section">
      <SectionHeader title="Plan" subtitle={turn.liveQueries?.length ? `${turn.liveQueries.length} queries` : "not yet planned"} mono />
      {#if turn.livePlan}
        <pre class="plan">{turn.livePlan}</pre>
      {:else}
        <p class="empty">The planner's approach will appear here.</p>
      {/if}
      {#if turn.liveQueries?.length}
        <ul class="queries">
          {#each turn.liveQueries as q}
            <li>{q}</li>
          {/each}
        </ul>
      {/if}
    </div>

    <SelfCritiquePanel history={critiqueHistory} result={turn.result ?? null} />

    {#if done && turn.result}
      <RunSummary
        query={turn.query}
        result={turn.result}
        confidence={turn.confidence ?? turn.result.confidence ?? undefined}
        goalStatus={turn.goalStatus ?? turn.result.goal_status ?? ""}
        runMode={turn.runMode ?? "studio"}
        savedPath={turn.savedPath ?? turn.result.report_path ?? undefined}
        learningPath={turn.learningPath ?? turn.result.learning_path ?? undefined}
        indexed={turn.indexed ?? false}
        onOpenPath={openPath}
      />
    {/if}
  </aside>
{/if}

<style>
  .inspector {
    flex: 0 0 300px;
    width: 300px;
    min-height: 0;
    overflow-y: auto;
    border-left: 1px solid var(--border-subtle);
    background: var(--bg-elevated);
    padding: 0.85rem 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  @media (max-width: 1100px) {
    .inspector {
      display: none;
    }
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .plan {
    margin: 0;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    line-height: 1.5;
    color: var(--text-muted);
    white-space: pre-wrap;
    word-break: break-word;
  }

  .queries {
    margin: 0;
    padding-left: 1.05rem;
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.5;
  }

  .empty {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }
</style>
