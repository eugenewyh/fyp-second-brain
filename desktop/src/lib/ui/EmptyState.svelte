<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title: string;
    description?: string;
    icon?: Snippet;
    action?: Snippet;
    class?: string;
  }

  let {
    title,
    description = "",
    icon,
    action,
    class: className = "",
  }: Props = $props();
</script>

<div class="empty-state {className}">
  {#if icon}
    <div class="icon" aria-hidden="true">
      {@render icon()}
    </div>
  {/if}
  <h3 class="title">{title}</h3>
  {#if description}
    <p class="desc">{description}</p>
  {/if}
  {#if action}
    <div class="action">
      {@render action()}
    </div>
  {/if}
</div>

<style>
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
    gap: var(--space-2);
    padding: var(--space-5) 0;
    color: var(--text-muted);
  }

  .icon {
    display: none;
  }

  .title {
    font-size: var(--text-lg);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .desc {
    font-size: var(--text-sm);
    color: var(--text-faint);
    line-height: 1.5;
    max-width: 28rem;
  }

  .action {
    margin-top: var(--space-2);
  }
</style>
