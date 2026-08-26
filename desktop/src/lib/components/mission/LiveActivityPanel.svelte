<script lang="ts">
  import type { ActivityLogEntry } from "$lib/research/agent-graph";
  import LogLine from "$lib/ui/LogLine.svelte";
  import SectionHeader from "$lib/ui/SectionHeader.svelte";

  interface Props {
    entries: ActivityLogEntry[];
    class?: string;
  }

  let { entries, class: className = "" }: Props = $props();

  let scroller: HTMLDivElement | undefined = $state();

  $effect(() => {
    void entries.length;
    if (scroller) {
      scroller.scrollTop = scroller.scrollHeight;
    }
  });
</script>

<aside class="live-activity {className}" data-testid="live-activity">
  <SectionHeader title="Trace" subtitle="Agent activity" mono />
  <div class="log ui-scroll" bind:this={scroller}>
    {#if entries.length === 0}
      <p class="empty">No events yet.</p>
    {:else}
      {#each entries as entry (entry.id)}
        <LogLine
          time={entry.time}
          agent={entry.agent}
          message={entry.message}
          tone={entry.tone}
        />
      {/each}
    {/if}
  </div>
</aside>

<style>
  .live-activity {
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-3);
  }

  .log {
    flex: 1;
    min-height: 0;
    max-height: 100%;
    overflow-y: auto;
  }

  .empty {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-faint);
    padding: 0.5rem 0;
  }
</style>
