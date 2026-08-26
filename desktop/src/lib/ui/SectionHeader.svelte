<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title: string;
    subtitle?: string;
    mono?: boolean;
    actions?: Snippet;
    class?: string;
  }

  let {
    title,
    subtitle = "",
    mono = false,
    actions,
    class: className = "",
  }: Props = $props();
</script>

<header class="section-header {className}" class:mono>
  <div class="text">
    <h3 class="title">{title}</h3>
    {#if subtitle}
      <p class="sub">{subtitle}</p>
    {/if}
  </div>
  {#if actions}
    <div class="actions">{@render actions()}</div>
  {/if}
</header>

<style>
  .section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    margin-bottom: var(--space-3);
  }

  .title {
    font-size: var(--type-caption-size);
    font-weight: var(--type-caption-weight);
    line-height: var(--type-caption-leading);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .mono .title {
    /* Captions stay Inter; mono only for true code surfaces */
    font-family: var(--font-sans);
  }

  .sub {
    margin-top: 0.15rem;
    font-size: var(--type-body-sm-size);
    font-weight: var(--type-body-sm-weight);
    line-height: var(--type-body-sm-leading);
    color: var(--text-muted);
  }

  .actions {
    flex-shrink: 0;
  }
</style>
