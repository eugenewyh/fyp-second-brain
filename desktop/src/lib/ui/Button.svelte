<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "ghost" | "icon" | "live";
    type?: "button" | "submit";
    disabled?: boolean;
    class?: string;
    title?: string;
    "data-testid"?: string;
    onclick?: (e: MouseEvent) => void;
    children: Snippet;
  }

  let {
    variant = "secondary",
    type = "button",
    disabled = false,
    class: className = "",
    title,
    "data-testid": testId,
    onclick,
    children,
  }: Props = $props();
</script>

<button
  {type}
  {disabled}
  {title}
  data-testid={testId}
  class="ui-btn {variant} {className}"
  {onclick}
>
  {@render children()}
</button>

<style>
  .ui-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    border: none;
    font-size: var(--type-button-size);
    font-weight: var(--type-button-weight);
    line-height: var(--type-button-leading);
    letter-spacing: var(--type-button-tracking);
    min-height: 32px;
    border-radius: var(--radius-feedback);
    transition:
      background var(--duration-fast) var(--ease),
      color var(--duration-fast) var(--ease),
      border-color var(--duration-fast) var(--ease),
      box-shadow var(--duration-fast) var(--ease);
  }

  .primary {
    background: var(--accent);
    color: var(--accent-contrast);
    padding: 0.4rem 0.9rem;
    border: 1px solid color-mix(in srgb, var(--accent) 88%, #000);
  }

  .primary:hover:not(:disabled) {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
  }

  .primary:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .live {
    background: var(--accent-live);
    color: var(--accent-contrast);
    padding: 0.4rem 0.9rem;
  }

  .live:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .secondary {
    background: transparent;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 0.35rem 0.75rem;
  }

  .secondary:hover:not(:disabled) {
    background: var(--surface-hover);
    border-color: color-mix(in srgb, var(--text) 22%, transparent);
  }

  .ghost {
    background: transparent;
    color: var(--text-muted);
    padding: 0.3rem 0.5rem;
  }

  .ghost:hover:not(:disabled) {
    color: var(--text);
  }

  .icon {
    background: transparent;
    color: var(--text-muted);
    padding: 0.3rem;
    width: 32px;
    height: 32px;
    min-height: 32px;
  }

  .icon:hover:not(:disabled) {
    color: var(--text);
    background: var(--surface-hover);
  }
</style>
