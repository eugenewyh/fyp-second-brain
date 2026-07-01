<script lang="ts">
  interface Option {
    value: string;
    label: string;
  }

  interface Props {
    options: Option[];
    value: string;
    onchange?: (value: string) => void;
  }

  let { options, value = $bindable(""), onchange }: Props = $props();

  function select(v: string) {
    value = v;
    onchange?.(v);
  }
</script>

<div class="segmented" role="group">
  {#each options as opt}
    <button
      type="button"
      class="seg-btn"
      class:active={value === opt.value}
      onclick={() => select(opt.value)}
    >
      {opt.label}
    </button>
  {/each}
</div>

<style>
  .segmented {
    display: flex;
    gap: 2px;
    padding: 2px;
    background: var(--bg);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
  }

  .seg-btn {
    flex: 1;
    padding: 0.3rem 0.4rem;
    font-size: 0.65rem;
    font-weight: 500;
    background: transparent;
    color: var(--text-faint);
    border-radius: 3px;
  }

  .seg-btn:hover {
    color: var(--text-muted);
    background: var(--surface-hover);
  }

  .seg-btn.active {
    background: var(--surface-hover);
    color: var(--text);
    box-shadow: inset 0 -1px 0 var(--accent);
  }
</style>