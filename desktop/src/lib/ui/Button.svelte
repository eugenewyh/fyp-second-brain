<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    variant?: "primary" | "secondary" | "ghost" | "icon";
    type?: "button" | "submit";
    disabled?: boolean;
    class?: string;
    title?: string;
    onclick?: (e: MouseEvent) => void;
    children: Snippet;
  }

  let {
    variant = "secondary",
    type = "button",
    disabled = false,
    class: className = "",
    title,
    onclick,
    children,
  }: Props = $props();
</script>

<button
  {type}
  {disabled}
  {title}
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
    font-weight: 500;
    transition: background 0.12s, color 0.12s;
  }

  .primary {
    background: var(--accent);
    color: #fff;
    padding: 0.45rem 0.75rem;
    font-size: 0.8125rem;
    border-radius: var(--radius-sm);
  }

  .primary:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .secondary {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 0.45rem 0.75rem;
    font-size: 0.8125rem;
    border-radius: var(--radius-sm);
  }

  .secondary:hover:not(:disabled) {
    background: var(--surface-hover);
  }

  .ghost {
    background: transparent;
    color: var(--text-muted);
    padding: 0.35rem 0.5rem;
    font-size: 0.75rem;
    border-radius: var(--radius-sm);
  }

  .ghost:hover:not(:disabled) {
    background: var(--surface-hover);
    color: var(--text);
  }

  .icon {
    background: transparent;
    color: var(--text-muted);
    padding: 0.35rem;
    border-radius: var(--radius-sm);
    width: 28px;
    height: 28px;
  }

  .icon:hover:not(:disabled) {
    background: var(--surface-hover);
    color: var(--text);
  }
</style>