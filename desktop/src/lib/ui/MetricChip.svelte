<script lang="ts">
  interface Props {
    label: string;
    value: string | number;
    tone?: "default" | "live" | "success" | "warning" | "error";
    class?: string;
  }

  let {
    label,
    value,
    tone = "default",
    class: className = "",
  }: Props = $props();
</script>

<span class="metric-chip tone-{tone} {className}">
  <span class="label">{label}</span>
  <span class="value">{value}</span>
</span>

<style>
  .metric-chip {
    display: inline-flex;
    align-items: baseline;
    gap: 0.35rem;
    padding: 0.15rem 0.45rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    background: var(--bg-elevated);
    font-size: var(--text-xs);
    line-height: 1.3;
  }

  .label {
    color: var(--text-faint);
    font-weight: var(--font-normal);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    font-size: var(--text-2xs);
  }

  .value {
    font-family: var(--font-mono);
    color: var(--text-muted);
    font-weight: var(--font-medium);
  }

  .tone-live .value {
    color: var(--accent-link);
  }

  .tone-success .value {
    color: var(--success);
  }

  .tone-warning .value {
    color: var(--warning);
  }

  .tone-error .value {
    color: var(--error);
  }
</style>
