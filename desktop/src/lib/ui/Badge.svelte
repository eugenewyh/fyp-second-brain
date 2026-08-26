<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "default" | "success" | "warning" | "error" | "live" | "accent";
    class?: string;
    children: Snippet;
  }

  let {
    variant = "default",
    class: className = "",
    children,
  }: Props = $props();
</script>

<span class="ui-badge v-{variant} {className}">
  {@render children()}
</span>

<style>
  .ui-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.1rem 0.4rem;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-muted);
    white-space: nowrap;
    max-width: 100%;
    letter-spacing: 0.01em;
  }

  .v-default {
    color: var(--text-muted);
  }

  .v-live,
  .v-accent {
    color: var(--text);
    border-color: var(--border);
    background: var(--surface-hover);
  }

  .v-success {
    color: var(--success);
    border-color: color-mix(in srgb, var(--success) 35%, var(--border));
    background: var(--success-dim);
  }

  .v-warning {
    color: var(--warning);
    border-color: color-mix(in srgb, var(--warning) 30%, var(--border));
    background: var(--warning-dim);
  }

  .v-error {
    color: var(--error);
    border-color: color-mix(in srgb, var(--error) 30%, var(--border));
    background: var(--error-dim);
  }
</style>
