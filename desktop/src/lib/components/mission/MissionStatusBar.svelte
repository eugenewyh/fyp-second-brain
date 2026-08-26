<script lang="ts">
  interface Props {
    detail?: string;
    runMode?: "studio" | "goal";
    goalPass?: number;
    goalMaxPasses?: number;
    memoryRecalled?: number;
    memoryDetail?: string;
    confidence?: number;
    goalStatus?: string;
    status?: string;
  }

  let {
    detail = "",
    runMode = "studio",
    goalPass,
    goalMaxPasses,
    memoryRecalled,
    memoryDetail = "",
    confidence,
    goalStatus = "",
    status = "",
  }: Props = $props();

  const confLabel = $derived(
    confidence == null || Number.isNaN(confidence)
      ? null
      : `${Math.round(confidence * 100)}%`,
  );
</script>

<div class="status-bar" data-testid="mission-status-bar">
  <div class="row">
    <span class="mode" class:goal={runMode === "goal"}>
      {runMode === "goal" ? "Goal" : "Studio"}
    </span>
    {#if runMode === "goal" && goalPass && goalMaxPasses}
      <span class="chip">Pass {goalPass}/{goalMaxPasses}</span>
    {/if}
    {#if goalStatus}
      <span class="chip">{goalStatus}</span>
    {/if}
    {#if confLabel}
      <span class="chip conf">Confidence {confLabel}</span>
    {/if}
    {#if memoryRecalled != null && memoryRecalled > 0}
      <span class="chip mem">Recalled {memoryRecalled}</span>
    {/if}
    {#if status === "running"}
      <span class="pulse" aria-hidden="true"></span>
    {/if}
  </div>
  {#if detail}
    <p class="detail">{detail}</p>
  {/if}
  {#if memoryDetail}
    <p class="mem-detail">{memoryDetail}</p>
  {/if}
</div>

<style>
  .status-bar {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    padding: 0.5rem 0.65rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
  }
  .mode {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-muted);
    padding: 0.15rem 0.4rem;
    border-radius: var(--radius-xs);
    border: 1px solid var(--border-subtle);
  }
  .mode.goal {
    color: var(--text);
    border-color: var(--text-faint);
  }
  .chip {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    color: var(--text-muted);
    padding: 0.12rem 0.4rem;
    border-radius: var(--radius-full);
    background: var(--bg);
    border: 1px solid var(--border-subtle);
  }
  .chip.conf {
    color: var(--text);
  }
  .chip.mem {
    color: var(--text-muted);
  }
  .detail,
  .mem-detail {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.35;
  }
  .mem-detail {
    color: var(--text-faint);
  }
  .pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text);
    animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse {
    0%,
    100% {
      opacity: 0.35;
    }
    50% {
      opacity: 1;
    }
  }
</style>
