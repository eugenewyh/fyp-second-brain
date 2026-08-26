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
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    background: var(--control-fill);
  }

  .seg-btn {
    min-height: 28px;
    padding: 0.3rem 0.75rem;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    background: transparent;
    color: var(--text-faint);
    border-radius: 0;
    border: none;
  }

  .seg-btn:hover {
    color: var(--text-muted);
    background: color-mix(in srgb, var(--surface-hover) 70%, transparent);
  }

  .seg-btn.active {
    background: var(--accent-live-dim);
    color: var(--accent-link);
  }
</style>
