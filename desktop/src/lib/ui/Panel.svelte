<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title?: string;
    description?: string;
    flush?: boolean;
    children: Snippet;
    actions?: Snippet;
  }

  let { title, description, flush = false, children, actions }: Props = $props();
</script>

<section class="ui-panel" class:flush>
  {#if title || actions}
    <header class="panel-header">
      <div>
        {#if title}<h2>{title}</h2>{/if}
        {#if description}<p class="desc">{description}</p>{/if}
      </div>
      {#if actions}<div class="actions">{@render actions()}</div>{/if}
    </header>
  {/if}
  <div class="panel-body">
    {@render children()}
  </div>
</section>

<style>
  .ui-panel {
    max-width: 720px;
  }

  .ui-panel.flush {
    max-width: none;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .panel-header h2 {
    font-size: var(--text-lg);
    font-weight: var(--font-medium);
    color: var(--text);
    line-height: 1.3;
  }

  .desc {
    margin-top: 0.2rem;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .actions {
    flex-shrink: 0;
  }
</style>