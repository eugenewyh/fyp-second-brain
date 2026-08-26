<script lang="ts">
  import { assistant } from "$lib/stores/assistant.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { folderLabel } from "$lib/assistant/workspace-chats";
  import { Circle } from "@lucide/svelte";

  const runningJobs = $derived(assistant.listRunningJobs());

  function openJob(sessionId: string, projectPath: string | null) {
    if (projectPath) workspace.setActiveTopic(projectPath);
    tabs.openSessionTab(sessionId);
    app.openHome();
  }

  function jobLabel(job: (typeof runningJobs)[number]): string {
    const channel = folderLabel(job.projectPath);
    const brief = job.label.length > 40 ? `${job.label.slice(0, 39)}…` : job.label;
    if (channel) return `#${channel} · ${brief}`;
    return brief;
  }
</script>

<footer class="statusbar" aria-label="Application status">
  <div class="left">
    <span class="chip" class:ok={connection.connected} title="Python sidecar">
      <Circle size={8} strokeWidth={0} fill="currentColor" />
      {connection.connected ? "Sidecar ready" : "Sidecar offline"}
    </span>
    {#if connection.watchPlanError}
      <span class="sep" aria-hidden="true">·</span>
      <span class="chip warn" title={connection.watchPlanError}>Watch planner error</span>
    {/if}
    {#if connection.briefsToday > 0}
      <span class="sep" aria-hidden="true">·</span>
      <button
        type="button"
        class="chip action"
        title="Open Watch to read your briefs"
        onclick={() => app.openWatch()}
      >
        {connection.briefsToday === 1
          ? "1 brief ready"
          : `${connection.briefsToday} briefs ready`}
      </button>
    {/if}
    <span class="sep" aria-hidden="true">·</span>
    <span class="chip muted" title="Vault file watcher">
      {workspace.watcherStatus === "idle" ? "Watcher idle" : workspace.watcherStatus}
    </span>
    {#if connection.collectionCount > 0}
      <span class="sep" aria-hidden="true">·</span>
      <span class="chip muted">{connection.collectionCount.toLocaleString()} mem</span>
    {/if}
  </div>
  <div class="right">
    {#each runningJobs.slice(0, 2) as job (job.sessionId)}
      <button
        type="button"
        class="chip action"
        class:live={!job.needsReview}
        class:review={job.needsReview}
        title={jobLabel(job)}
        onclick={() => openJob(job.sessionId, job.projectPath)}
      >
        {#if job.needsReview}
          <span class="badge">Review</span>
        {:else}
          <span class="pulse" aria-hidden="true"></span>
        {/if}
        {jobLabel(job)}
      </button>
    {/each}
    {#if runningJobs.length === 0}
      <span class="chip muted">Idle</span>
    {:else if runningJobs.length > 2}
      <span class="chip muted">+{runningJobs.length - 2} more</span>
    {/if}
  </div>
</footer>

<style>
  .statusbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    height: var(--statusbar-height);
    min-height: var(--statusbar-height);
    padding: 0 0.75rem;
    flex-shrink: 0;
    background: var(--pane-bg);
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .left,
  .right {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    min-width: 0;
  }

  .left {
    flex: 1;
    overflow: hidden;
  }

  .right {
    flex-shrink: 0;
    max-width: 52%;
    overflow: hidden;
  }

  .sep {
    color: var(--border);
    user-select: none;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    max-width: 12rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-muted);
  }

  .chip.ok {
    color: var(--success);
  }

  .chip.warn {
    color: var(--error);
    max-width: 14rem;
  }

  .chip.muted {
    color: var(--text-faint);
  }

  .chip.action {
    border: none;
    background: transparent;
    padding: 0.15rem 0.4rem;
    border-radius: var(--radius-feedback);
    min-height: 22px;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    cursor: pointer;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
    max-width: 16rem;
  }

  .chip.action:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .chip.action.live {
    color: var(--accent-live);
    background: var(--accent-live-dim);
  }

  .chip.action.review {
    color: var(--warning);
    background: var(--warning-dim);
  }

  .badge {
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    font-weight: var(--font-semibold);
  }

  .pulse {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
    flex-shrink: 0;
    animation: pulse-live 1.4s ease-in-out infinite;
  }
</style>
