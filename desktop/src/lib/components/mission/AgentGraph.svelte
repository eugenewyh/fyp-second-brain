<script lang="ts">
  import {
    AGENT_NODES,
    type AgentNodeId,
    type AgentNodeStatus,
  } from "$lib/research/agent-graph";
  import type { ActivityLogEntry } from "$lib/research/agent-graph";
  import {
    Map,
    Search,
    Brain,
    ShieldCheck,
    PenLine,
    Check,
    Loader2,
    RefreshCw,
    AlertCircle,
  } from "@lucide/svelte";

  interface Props {
    statuses: Record<AgentNodeId, AgentNodeStatus>;
    selected?: AgentNodeId | null;
    looping?: boolean;
    /** Live status line from the stream */
    detail?: string;
    /** Optional recent activity lines */
    activityLog?: ActivityLogEntry[];
    onSelect?: (id: AgentNodeId) => void;
  }

  let {
    statuses,
    selected = null,
    looping = false,
    detail = "",
    activityLog = [],
    onSelect,
  }: Props = $props();

  const ICONS: Record<AgentNodeId, typeof Map> = {
    planner: Map,
    retriever: Search,
    analyst: Brain,
    verifier: ShieldCheck,
    synthesizer: PenLine,
  };

  const VERBS: Record<AgentNodeId, string> = {
    planner: "Breaking down the question",
    retriever: "Searching your library & sources",
    analyst: "Extracting insights",
    verifier: "Critiquing the analysis",
    synthesizer: "Writing the report",
  };

  const order = AGENT_NODES.map((n) => n.id);

  /** Prefer live agent; else next pending (not last done — avoids “Retriever finished” mid-run). */
  const activeId = $derived.by((): AgentNodeId | null => {
    for (const id of order) {
      const s = statuses[id];
      if (s === "running" || s === "iterating" || s === "waiting_review" || s === "error") {
        return id;
      }
    }
    for (const id of order) {
      if ((statuses[id] ?? "pending") === "pending") return id;
    }
    // Truly complete
    return order[order.length - 1] ?? null;
  });

  const focusId = $derived(selected ?? activeId);
  const rawFocusStatus = $derived(
    focusId ? (statuses[focusId] ?? "pending") : "pending",
  );
  /** UI status: don't present intermediate agents as the mission being “done”. */
  const focusStatus = $derived.by((): AgentNodeStatus => {
    if (!focusId) return "pending";
    const st = statuses[focusId] ?? "pending";
    const allDone = order.every((id) => statuses[id] === "done");
    if (st === "done" && !allDone && selected === focusId) {
      // User clicked a completed step — still show done for that step
      return "done";
    }
    if (st === "done" && !allDone && selected == null) {
      // Shouldn't happen with activeId logic, but guard
      return "pending";
    }
    return st;
  });
  const FocusIcon = $derived(focusId ? ICONS[focusId] : Brain);

  const doneCount = $derived(order.filter((id) => statuses[id] === "done").length);
  const allDone = $derived(doneCount === order.length);
  const hasRunning = $derived(
    order.some((id) => {
      const s = statuses[id];
      return s === "running" || s === "iterating" || s === "waiting_review";
    }),
  );
  // Progress: full steps done + half credit if something is actively running
  const progress = $derived(
    Math.min(
      100,
      Math.round(((doneCount + (hasRunning ? 0.45 : 0)) / order.length) * 100),
    ),
  );

  const focusLabel = $derived(
    focusId ? (AGENT_NODES.find((n) => n.id === focusId)?.label ?? "Agent") : "Agents",
  );

  const headline = $derived.by(() => {
    if (!focusId) return "Starting…";
    const st = statuses[focusId] ?? "pending";
    if (st === "waiting_review") return "Waiting for plan approval";
    if (st === "iterating") return "Revising after critique";
    if (st === "error") return "Stopped — see error below";
    if (allDone) return "Mission complete";
    if (st === "running") return VERBS[focusId];
    if (st === "pending") {
      if (doneCount === 0) return "Starting multi-agent research…";
      return `Up next: ${focusLabel}`;
    }
    // Selected a completed step while mission still running
    if (st === "done" && !allDone) return `${focusLabel} completed this stage`;
    return VERBS[focusId];
  });

  const statusBadge = $derived.by(() => {
    if (allDone) return "done";
    if (focusStatus === "waiting_review") return "review";
    if (focusStatus === "pending" && doneCount > 0) return "next";
    if (focusStatus === "pending") return "starting";
    return focusStatus;
  });

  const subline = $derived.by(() => {
    const d = detail?.trim() ?? "";
    if (d) return d;
    if (looping) return "Critique loop — refining analysis";
    if (allDone) return "Report ready";
    if (focusStatus === "pending" && doneCount > 0) {
      return "Handing off to the next agent…";
    }
    if (focusStatus === "pending") return "Warming up";
    if (focusStatus === "running") return "Working…";
    return "";
  });

  const recentActivity = $derived(
    (activityLog ?? []).slice(-3).reverse(),
  );

  function stClass(s: AgentNodeStatus): string {
    return `st-${s}`;
  }
</script>

<div class="mission" data-testid="agent-graph">
  <!-- Progress rail -->
  <div class="rail" role="group" aria-label="Research stages">
    {#each AGENT_NODES as node, i}
      {@const st = statuses[node.id] ?? "pending"}
      {@const Icon = ICONS[node.id]}
      {@const isFocus = focusId === node.id}
      <button
        type="button"
        class="step {stClass(st)}"
        class:focus={isFocus}
        class:loop-hot={looping && (node.id === "analyst" || node.id === "verifier")}
        aria-current={isFocus ? "step" : undefined}
        title="{node.label}: {st}"
        onclick={() => onSelect?.(node.id)}
      >
        <span class="step-orb">
          {#if st === "done"}
            <Check size={14} strokeWidth={2.5} />
          {:else if st === "running"}
            <span class="spin"><Loader2 size={14} strokeWidth={2} /></span>
          {:else if st === "iterating"}
            <span class="spin-slow"><RefreshCw size={13} strokeWidth={2} /></span>
          {:else if st === "error"}
            <AlertCircle size={14} strokeWidth={2} />
          {:else if st === "waiting_review"}
            <Icon size={13} strokeWidth={1.85} />
          {:else}
            <Icon size={13} strokeWidth={1.75} />
          {/if}
        </span>
        <span class="step-label">{node.short}</span>
      </button>
      {#if i < AGENT_NODES.length - 1}
        {@const next = AGENT_NODES[i + 1]}
        {@const fromDone = st === "done" || st === "running" || st === "iterating"}
        {@const toLive =
          statuses[next.id] === "running" ||
          statuses[next.id] === "iterating" ||
          statuses[next.id] === "done"}
        <div
          class="seg"
          class:lit={fromDone}
          class:flow={fromDone && (statuses[next.id] === "running" || statuses[next.id] === "iterating")}
          class:to-done={toLive && st === "done"}
          aria-hidden="true"
        ></div>
      {/if}
    {/each}
  </div>

  <!-- Focus card -->
  <div
    class="focus-card {stClass(focusStatus)}"
    class:looping
    class:between={statusBadge === "next" || statusBadge === "starting"}
  >
    <div class="focus-main">
      <div class="focus-icon-wrap">
        <FocusIcon size={20} strokeWidth={1.75} />
        {#if focusStatus === "running" || focusStatus === "iterating" || statusBadge === "next"}
          <span class="pulse-ring" aria-hidden="true"></span>
        {/if}
      </div>
      <div class="focus-copy">
        <div class="focus-meta">
          <span class="agent-name">{focusLabel}</span>
          <span class="agent-st" data-badge={statusBadge}>{statusBadge}</span>
          {#if looping}
            <span class="loop-pill">revise loop</span>
          {/if}
        </div>
        <p class="headline">{headline}</p>
        {#if subline}
          <p class="subline">
            <span
              class="live-dot"
              class:on={focusStatus === "running" ||
                focusStatus === "iterating" ||
                statusBadge === "next"}
            ></span>
            {subline}
          </p>
        {/if}
      </div>
      <div class="pct" aria-hidden="true">
        <span class="pct-num">{progress}%</span>
        <span class="pct-lab">{allDone ? "done" : "in progress"}</span>
      </div>
    </div>

    <div class="bar" aria-hidden="true">
      <div class="bar-fill" style="width: {progress}%"></div>
    </div>

    {#if recentActivity.length > 0 && (focusStatus === "running" || focusStatus === "iterating")}
      <ul class="activity">
        {#each recentActivity as entry (entry.id)}
          <li class="act" class:live={entry.tone === "live"} class:warn={entry.tone === "warning"}>
            <span class="act-agent">{entry.agent}</span>
            <span class="act-msg">{entry.message}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .mission {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    min-width: 0;
  }

  /* —— Rail —— */
  .rail {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 0.15rem 0.1rem;
    overflow-x: auto;
  }

  .step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    background: transparent;
    padding: 0.25rem 0.2rem;
    min-height: auto;
    border-radius: var(--radius-lg);
    flex-shrink: 0;
    color: var(--text-faint);
  }

  .step:hover {
    color: var(--text-muted);
  }

  .step-orb {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    border: 1.5px solid var(--border);
    background: var(--surface);
    color: var(--text-faint);
    transition:
      border-color 160ms ease,
      background 160ms ease,
      color 160ms ease;
  }

  .step-label {
    font-size: var(--text-2xs);
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .step.st-done .step-orb {
    border-color: color-mix(in srgb, var(--success) 55%, var(--border));
    background: var(--success-dim);
    color: var(--success);
  }

  .step.st-done .step-label {
    color: var(--text-muted);
  }

  .step.st-running .step-orb {
    border-color: var(--accent-live);
    background: var(--accent-live-dim);
    color: var(--accent-link);
  }

  .step.st-running .step-label {
    color: var(--accent-link);
  }

  .step.st-iterating .step-orb {
    border-color: var(--warning);
    background: var(--warning-dim);
    color: var(--warning);
  }

  .step.st-iterating .step-label {
    color: var(--warning);
  }

  .step.st-error .step-orb {
    border-color: var(--error);
    background: var(--error-dim);
    color: var(--error);
  }

  .step.st-waiting_review .step-orb {
    border-color: color-mix(in srgb, var(--accent-live) 50%, var(--border));
    background: var(--accent-live-dim);
    color: var(--accent-link);
  }

  .step.focus .step-orb {
    border-color: var(--accent-live);
  }

  .step.st-pending .step-orb {
    opacity: 0.7;
  }

  .seg {
    flex: 1;
    min-width: 0.65rem;
    max-width: 2.5rem;
    height: 2px;
    margin: 0 0.15rem 1.1rem;
    border-radius: var(--radius-xs);
    background: var(--border-subtle);
    align-self: center;
    position: relative;
    overflow: hidden;
  }

  .seg.lit,
  .seg.to-done {
    background: color-mix(in srgb, var(--success) 40%, var(--border));
  }

  .seg.flow {
    background: color-mix(in srgb, var(--accent-live) 35%, var(--border));
  }

  .seg.flow::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
      90deg,
      transparent,
      color-mix(in srgb, var(--accent-link) 90%, white),
      transparent
    );
    animation: seg-flow 1.1s linear infinite;
  }

  /* —— Focus card —— */
  .focus-card {
    position: relative;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--pane-bg);
    padding: 0.9rem 1rem 0.85rem;
    overflow: hidden;
  }

  .focus-main {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .focus-icon-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: var(--radius-lg);
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .focus-card.st-running .focus-icon-wrap {
    color: var(--accent-link);
    border-color: color-mix(in srgb, var(--accent-live) 40%, var(--border));
    background: var(--accent-live-dim);
  }

  .focus-card.st-done .focus-icon-wrap {
    color: var(--success);
    border-color: color-mix(in srgb, var(--success) 35%, var(--border));
    background: var(--success-dim);
  }

  .focus-card.st-iterating .focus-icon-wrap {
    color: var(--warning);
    border-color: color-mix(in srgb, var(--warning) 40%, var(--border));
    background: var(--warning-dim);
  }

  .focus-card.st-error .focus-icon-wrap {
    color: var(--error);
    border-color: color-mix(in srgb, var(--error) 40%, var(--border));
    background: var(--error-dim);
  }

  .pulse-ring {
    position: absolute;
    inset: -4px;
    border-radius: var(--radius-lg);
    border: 1.5px solid var(--accent-live);
    animation: pulse-out 1.6s ease-out infinite;
    pointer-events: none;
  }

  .focus-card.st-iterating .pulse-ring {
    border-color: var(--warning);
  }

  .focus-copy {
    flex: 1;
    min-width: 0;
  }

  .focus-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.25rem;
  }

  .agent-name {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .agent-st {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
  }

  .agent-st[data-badge="running"],
  .agent-st[data-badge="next"],
  .agent-st[data-badge="starting"],
  .agent-st[data-badge="review"] {
    color: var(--accent-link);
  }

  .agent-st[data-badge="done"] {
    color: var(--success);
  }

  .agent-st[data-badge="iterating"] {
    color: var(--warning);
  }

  .agent-st[data-badge="error"] {
    color: var(--error);
  }

  .focus-card.between .focus-icon-wrap {
    color: var(--accent-link);
    border-color: color-mix(in srgb, var(--accent-live) 35%, var(--border));
    background: var(--accent-live-dim);
  }

  .loop-pill {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--warning);
    background: var(--warning-dim);
    border: 1px solid color-mix(in srgb, var(--warning) 30%, transparent);
    border-radius: var(--radius-full);
    padding: 0.1rem 0.4rem;
  }

  .headline {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
    letter-spacing: -0.01em;
    line-height: 1.35;
  }

  .subline {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.3rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.4;
  }

  .live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-faint);
    flex-shrink: 0;
  }

  .live-dot.on {
    background: var(--accent-live);
    animation: live-pulse 1.4s ease-in-out infinite;
  }

  .pct {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    flex-shrink: 0;
    padding-top: 0.1rem;
  }

  .pct-num {
    font-family: var(--font-mono);
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    letter-spacing: -0.02em;
  }

  .pct-lab {
    font-size: var(--text-2xs);
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
  }

  .bar {
    margin-top: 0.75rem;
    height: 3px;
    border-radius: var(--radius-xs);
    background: var(--border-subtle);
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: var(--radius-xs);
    background: linear-gradient(
      90deg,
      color-mix(in srgb, var(--accent-live) 70%, var(--success)),
      var(--accent-link)
    );
    transition: width 280ms ease;
  }

  .focus-card.st-done .bar-fill {
    background: var(--success);
  }

  .activity {
    list-style: none;
    margin-top: 0.7rem;
    padding-top: 0.55rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .act {
    display: flex;
    gap: 0.5rem;
    font-size: var(--text-xs);
    line-height: 1.35;
    color: var(--text-faint);
  }

  .act-agent {
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    flex-shrink: 0;
    min-width: 4.5rem;
    color: var(--text-faint);
  }

  .act-msg {
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .act.live .act-agent {
    color: var(--accent-link);
  }

  .act.warn .act-agent {
    color: var(--warning);
  }

  .spin {
    display: inline-flex;
    animation: spin 0.9s linear infinite;
  }

  .spin-slow {
    display: inline-flex;
    animation: spin 1.4s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes seg-flow {
    to {
      transform: translateX(100%);
    }
  }

  @keyframes pulse-out {
    0% {
      opacity: 0.55;
      transform: scale(0.96);
    }
    100% {
      opacity: 0;
      transform: scale(1.2);
    }
  }

  @keyframes live-pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.55;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spin,
    .spin-slow,
    .seg.flow::after,
    .pulse-ring,
    .live-dot.on {
      animation: none !important;
    }
  }
</style>
