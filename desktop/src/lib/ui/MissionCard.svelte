<script lang="ts">
  import type { Snippet } from "svelte";
  import SectionHeader from "./SectionHeader.svelte";

  interface Props {
    title?: string;
    subtitle?: string;
    live?: boolean;
    class?: string;
    children: Snippet;
    actions?: Snippet;
  }

  let {
    title = "",
    subtitle = "",
    live = false,
    class: className = "",
    children,
    actions,
  }: Props = $props();
</script>

<section class="mission-card {className}" class:live>
  {#if title}
    <SectionHeader {title} {subtitle} mono>
      {#snippet actions()}
        {#if actions}{@render actions()}{/if}
      {/snippet}
    </SectionHeader>
  {/if}
  <div class="body">
    {@render children()}
  </div>
</section>

<style>
  .mission-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-4);
  }

  .mission-card.live {
    border-color: var(--border-active);
  }

  .body {
    min-width: 0;
  }
</style>
