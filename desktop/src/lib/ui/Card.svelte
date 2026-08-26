<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    class?: string;
    padding?: "sm" | "md" | "lg";
    elevated?: boolean;
    live?: boolean;
    children: Snippet;
  }

  let {
    class: className = "",
    padding = "md",
    elevated = false,
    live = false,
    children,
  }: Props = $props();
</script>

<div
  class="ui-card pad-{padding} {className}"
  class:elevated
  class:live
>
  {@render children()}
</div>

<style>
  .ui-card {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    box-shadow: none;
  }

  .elevated {
    background: var(--bg-elevated);
    border-color: var(--border);
  }

  .live {
    border-color: var(--border-active);
    box-shadow: inset 0 0 0 1px var(--accent-live-dim);
  }

  .pad-sm {
    padding: var(--space-3);
  }

  .pad-md {
    padding: var(--space-4);
  }

  .pad-lg {
    padding: var(--space-5);
  }
</style>
