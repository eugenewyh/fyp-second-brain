<script lang="ts">
  interface Props {
    value?: string;
    placeholder?: string;
    variant?: "default" | "search";
    disabled?: boolean;
    class?: string;
    oninput?: (e: Event) => void;
    onkeydown?: (e: KeyboardEvent) => void;
  }

  let {
    value = $bindable(""),
    placeholder = "",
    variant = "default",
    disabled = false,
    class: className = "",
    oninput,
    onkeydown,
  }: Props = $props();
</script>

<input
  class="ui-input {variant} {className}"
  bind:value
  {placeholder}
  {disabled}
  {oninput}
  {onkeydown}
/>

<style>
  .ui-input {
    width: 100%;
    font-size: 0.8125rem;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.5rem 0.65rem;
  }

  .search {
    background: var(--bg-elevated);
    border-color: var(--border-subtle);
    padding: 0.45rem 0.65rem;
    font-size: 0.75rem;
  }

  .ui-input:focus {
    outline: 2px solid var(--accent);
    outline-offset: 0;
    border-color: transparent;
  }
</style>