<script lang="ts">
  import { RefreshCw } from "@lucide/svelte";
  import Button from "$lib/ui/Button.svelte";
  import { failureCopy } from "$lib/research/status-copy";

  interface Props {
    error?: string | null;
    disabled?: boolean;
    detailsOpen?: boolean;
    onRetry: () => void;
    onDetails?: () => void;
  }

  let {
    error = null,
    disabled = false,
    detailsOpen = false,
    onRetry,
    onDetails,
  }: Props = $props();

  const copy = $derived(failureCopy(error));
</script>

<div class="fail" role="alert" data-testid="run-failed">
  <p class="fail-title">{copy.title}</p>
  <p class="fail-hint">{copy.hint}</p>
  <div class="fail-actions">
    <Button variant="primary" data-testid="retry-run" {disabled} onclick={onRetry}>
      <RefreshCw size={14} />
      Retry
    </Button>
    {#if onDetails}
      <button type="button" class="link" onclick={onDetails}>
        {detailsOpen ? "Hide details" : "Details"}
      </button>
    {/if}
  </div>
</div>

<style>
  .fail {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
    width: 100%;
    padding: 0.9rem 1rem;
    border: 1px solid color-mix(in srgb, var(--error) 22%, var(--border));
    background: var(--error-dim);
    border-radius: var(--radius-xl);
  }

  .fail-title {
    margin: 0;
    color: var(--text);
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    letter-spacing: -0.015em;
    line-height: 1.35;
  }

  .fail-hint {
    margin: 0;
    color: var(--text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
    max-width: 36rem;
  }

  .fail-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem 0.85rem;
    margin-top: 0.35rem;
  }

  .link {
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 0;
  }

  .link:hover {
    color: var(--text);
    text-decoration: underline;
  }
</style>
