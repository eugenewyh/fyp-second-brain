<script lang="ts">
  import { LLM_PROVIDERS, type LlmProviderId } from "$lib/llm/models";
  import {
    modelHint,
    modelsForProvider,
    shortModelLabel,
  } from "$lib/llm/models";

  type Provider = (typeof LLM_PROVIDERS)[number];

  interface Props {
    settingsForm: Record<string, string>;
    activeId: LlmProviderId;
    connectedList: Provider[];
    availableList: Provider[];
    saving: boolean;
    onConnect: (id: LlmProviderId) => void;
    onConfig: (id: LlmProviderId) => void;
    onUse: (id: LlmProviderId) => void;
    onDisconnect: (id: LlmProviderId) => void;
    onPersist: (partial: Record<string, string>) => void;
  }

  let {
    settingsForm,
    activeId,
    connectedList,
    availableList,
    saving,
    onConnect,
    onConfig,
    onUse,
    onDisconnect,
    onPersist,
  }: Props = $props();

  let showAdvanced = $state(false);

  const defaultModels = $derived(
    modelsForProvider(activeId, settingsForm.LLM_MODEL),
  );
  const fastModels = $derived(
    ["", ...modelsForProvider(activeId, settingsForm.LLM_FAST_MODEL)],
  );
  const fallbackModels = $derived(
    modelsForProvider(activeId, settingsForm.LLM_FALLBACK_MODEL),
  );

  function onDefaultChange(e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value;
    onPersist({ LLM_MODEL: value });
  }

  function onFastChange(e: Event) {
    onPersist({ LLM_FAST_MODEL: (e.currentTarget as HTMLSelectElement).value });
  }

  function onFallbackChange(e: Event) {
    onPersist({ LLM_FALLBACK_MODEL: (e.currentTarget as HTMLSelectElement).value });
  }
</script>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Providers</h3>
    <p class="st-card-sub">Bring your own keys. Only connected providers can run research.</p>
  </div>

  <h4 class="list-label">Connected</h4>
  {#if connectedList.length === 0}
    <p class="empty-line">No providers connected yet.</p>
  {:else}
    <ul class="provider-list">
      {#each connectedList as p (p.id)}
        <li class="provider-row" class:active={activeId === p.id}>
          <div class="prov-left">
            <span class="mono-badge">{p.monogram}</span>
            <div class="prov-text">
              <div class="prov-name-row">
                <span class="prov-name">{p.label}</span>
                {#if activeId === p.id}
                  <span class="badge-active">Active</span>
                {/if}
                {#if p.recommended}
                  <span class="badge-soft">Recommended</span>
                {/if}
              </div>
              <span class="prov-desc">{p.short}</span>
            </div>
          </div>
          <div class="prov-actions">
            {#if activeId !== p.id}
              <button
                type="button"
                class="btn-ghost"
                disabled={saving}
                onclick={() => onUse(p.id)}
              >
                Use
              </button>
            {/if}
            <button type="button" class="btn-ghost" onclick={() => onConfig(p.id)}>
              Config
            </button>
            {#if p.needsKey}
              <button
                type="button"
                class="btn-ghost danger"
                disabled={saving}
                onclick={() => onDisconnect(p.id)}
              >
                Disconnect
              </button>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {/if}

  {#if availableList.length}
    <h4 class="list-label spaced">Available</h4>
    <ul class="provider-list">
      {#each availableList as p (p.id)}
        <li class="provider-row">
          <div class="prov-left">
            <span class="mono-badge dim">{p.monogram}</span>
            <div class="prov-text">
              <div class="prov-name-row">
                <span class="prov-name">{p.label}</span>
                {#if p.recommended}
                  <span class="badge-soft">Recommended</span>
                {/if}
              </div>
              <span class="prov-desc">{p.short}</span>
            </div>
          </div>
          <div class="prov-actions">
            <button type="button" class="btn-connect" onclick={() => onConnect(p.id)}>
              + Connect
            </button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Default model</h3>
    <p class="st-card-sub">Used for planning and reports. Same list as the composer.</p>
  </div>
  <label class="st-field">
    <span class="st-field-label">Model</span>
    <select class="st-control" value={settingsForm.LLM_MODEL} onchange={onDefaultChange} disabled={saving}>
      {#each defaultModels as model}
        <option value={model}>
          {shortModelLabel(model)}{modelHint(model) ? ` — ${modelHint(model)}` : ""}
        </option>
      {/each}
    </select>
  </label>
</section>

<button
  type="button"
  class="st-advanced"
  onclick={() => (showAdvanced = !showAdvanced)}
  aria-expanded={showAdvanced}
>
  <span>{showAdvanced ? "Hide advanced" : "Show advanced"}</span>
  <span>{showAdvanced ? "▴" : "▾"}</span>
</button>

{#if showAdvanced}
  <section class="st-card muted">
    <div class="st-field-grid">
      <label class="st-field">
        <span class="st-field-label">Fast model (Ask / verifier) <span class="st-opt">optional</span></span>
        <select class="st-control" value={settingsForm.LLM_FAST_MODEL ?? ""} onchange={onFastChange} disabled={saving}>
          <option value="">Use default</option>
          {#each fastModels.filter(Boolean) as model}
            <option value={model}>{shortModelLabel(model)}</option>
          {/each}
        </select>
      </label>
      <label class="st-field">
        <span class="st-field-label">Fallback on rate limit</span>
        <select
          class="st-control"
          value={settingsForm.LLM_FALLBACK_MODEL}
          onchange={onFallbackChange}
          disabled={saving}
        >
          {#each fallbackModels as model}
            <option value={model}>{shortModelLabel(model)}</option>
          {/each}
        </select>
      </label>
    </div>
  </section>
{/if}

<style>
  .list-label {
    font-size: var(--type-caption-size);
    font-weight: var(--type-caption-weight);
    line-height: var(--type-caption-leading);
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
    text-transform: uppercase;
    margin-bottom: 0.45rem;
  }

  .list-label.spaced {
    margin-top: 1rem;
  }

  .empty-line {
    font-size: var(--text-sm);
    color: var(--text-faint);
    padding: 0.5rem 0;
  }

  .provider-list {
    list-style: none;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    overflow: hidden;
    background: var(--bg-elevated);
  }

  .provider-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.7rem 0.8rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .provider-row:last-child {
    border-bottom: none;
  }

  .provider-row.active {
    background: color-mix(in srgb, var(--accent-live) 8%, transparent);
  }

  .prov-left {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-width: 0;
  }

  .mono-badge {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.35rem;
    height: 2.35rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    font-family: var(--font-mono);
    background: color-mix(in srgb, var(--accent-live) 22%, var(--surface));
    color: var(--accent-link);
  }

  .mono-badge.dim {
    background: var(--surface);
    color: var(--text-faint);
  }

  .prov-text {
    min-width: 0;
  }

  .prov-name-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
  }

  .prov-name {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .prov-desc {
    display: block;
    font-size: var(--text-sm);
    color: var(--text-faint);
    margin-top: 0.1rem;
  }

  .badge-active {
    font-size: var(--text-2xs);
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--accent-link);
    background: var(--accent-live-dim);
    border-radius: var(--radius-xs);
    padding: 0.1rem 0.35rem;
  }

  .badge-soft {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-xs);
    padding: 0.1rem 0.35rem;
  }

  .prov-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    flex-shrink: 0;
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

  .btn-ghost.danger:hover:not(:disabled) {
    color: var(--error);
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

  .btn-connect:hover {
    background: var(--surface-hover);
    border-color: var(--border-active);
  }

  @media (max-width: 560px) {
    .provider-row {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
