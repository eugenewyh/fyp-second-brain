<script lang="ts">
  import { api, type LocalEngine } from "$lib/api";

  interface Props {
    engine: LocalEngine;
    active: boolean;
    saving: boolean;
    onEngine: (next: LocalEngine) => void;
    onUse: () => void;
  }

  let { engine, active, saving, onEngine, onUse }: Props = $props();

  let busy = $state(false);
  let error = $state("");

  const kind = $derived(engine.kind);

  $effect(() => {
    const k = kind;
    if (k !== "acquiring" && k !== "starting") return;
    const timer = setInterval(() => {
      void refresh();
    }, 1000);
    return () => clearInterval(timer);
  });

  async function refresh() {
    try {
      onEngine(await api.localEngine());
    } catch (e) {
      error = e instanceof Error ? e.message : "Couldn't read on-device status";
    }
  }

  async function prepare() {
    busy = true;
    error = "";
    try {
      onEngine(await api.localEngineEnsure());
    } catch (e) {
      error = e instanceof Error ? e.message : "Couldn't prepare on-device model";
    } finally {
      busy = false;
    }
  }

  function formatGb(bytes: number): string {
    const gb = bytes / 1e9;
    if (gb >= 10) return `${gb.toFixed(0)} GB`;
    if (gb >= 0.1) return `${gb.toFixed(1)} GB`;
    return `${Math.max(bytes, 0).toFixed(0)} B`;
  }

  function progressLabel(done: number, total: number): string {
    if (total <= 0) return formatGb(done);
    return `${formatGb(done)} / ${formatGb(total)}`;
  }
</script>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">On-device</h3>
    <p class="st-card-sub">Runs on this Mac. NVIDIA stays the included cloud default.</p>
  </div>

  {#if engine.kind === "unsupported"}
    <p class="status-line">{engine.detail}</p>
  {:else if engine.kind === "not_installed"}
    <p class="status-line">{engine.model.display_name}</p>
    <div class="actions">
      <button type="button" class="btn-connect" disabled={busy || saving} onclick={() => void prepare()}>
        {engine.download_bytes > 0 ? `Download ${formatGb(engine.download_bytes)}` : "Start"}
      </button>
    </div>
  {:else if engine.kind === "acquiring"}
    <p class="status-line">
      Downloading {engine.step}… {progressLabel(engine.done_bytes, engine.total_bytes)}
    </p>
  {:else if engine.kind === "starting"}
    <p class="status-line">Starting {engine.model.display_name}…</p>
  {:else if engine.kind === "ready"}
    <p class="status-line">{engine.model.display_name}</p>
    {#if !active}
      <div class="actions">
        <button type="button" class="btn-ghost" disabled={saving} onclick={onUse}>Use</button>
      </div>
    {:else}
      <p class="active-line">Active</p>
    {/if}
  {:else if engine.kind === "failed"}
    <p class="status-line error">{engine.message}</p>
    {#if engine.retryable}
      <div class="actions">
        <button type="button" class="btn-connect" disabled={busy || saving} onclick={() => void prepare()}>
          Retry
        </button>
      </div>
    {/if}
  {:else}
    {@const _exhaustive: never = engine}
  {/if}

  {#if error}
    <p class="status-line error">{error}</p>
  {/if}
</section>

<style>
  .status-line {
    font-size: var(--text-sm);
    color: var(--text);
    margin: 0;
  }

  .status-line.error {
    color: var(--error);
  }

  .active-line {
    font-size: var(--text-2xs);
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--accent-link);
    margin: 0.35rem 0 0;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    margin-top: 0.65rem;
  }

  .btn-ghost {
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-normal);
    min-height: 30px;
    padding: 0.25rem 0.55rem;
    border-radius: var(--radius-feedback);
  }

  .btn-ghost:hover:not(:disabled) {
    color: var(--text);
    background: var(--surface-hover);
  }

  .btn-connect {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    min-height: 32px;
    padding: 0.3rem 0.7rem;
    border-radius: var(--radius-md);
  }

  .btn-connect:hover:not(:disabled) {
    background: var(--surface-hover);
    border-color: var(--border-active);
  }
</style>
