<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { app } from "$lib/stores/app.svelte";

  interface Props {
    settingsForm: Record<string, string>;
    autoIngest: boolean;
    saving: boolean;
    onAutoIngest: (enabled: boolean) => void;
    onPersist: (partial: Record<string, string>) => void;
  }

  let { settingsForm, autoIngest, saving, onAutoIngest, onPersist }: Props = $props();

  let showAdvanced = $state(false);

  function onEmbedProvider(e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value;
    const model =
      value === "ollama"
        ? "nomic-embed-text"
        : value === "openai_compatible"
          ? "text-embedding-3-small"
          : "BAAI/bge-small-en-v1.5";
    onPersist({ EMBEDDING_PROVIDER: value, EMBEDDING_MODEL: model });
  }
</script>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Vault search</h3>
    <p class="st-card-sub">Bundled local embeddings by default — Ollama is not required.</p>
  </div>
  {#if connection.reindexRequired || !connection.embeddingsOk}
    <p class="embed-warn">
      {connection.embeddingsError ||
        (connection.reindexRequired
          ? "Re-ingest your vault so search matches the current embedding model."
          : "Embeddings are unavailable.")}
      <button type="button" class="linkish" onclick={() => app.openSheet("ingest")}>
        Open ingest
      </button>
    </p>
  {:else}
    <p class="embed-ok">
      Ready · {connection.embeddingsProvider || "fastembed"}
      {connection.embeddingsModel ? ` · ${connection.embeddingsModel}` : ""}
    </p>
  {/if}
</section>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Library</h3>
    <p class="st-card-sub">How new files enter your knowledge base.</p>
  </div>
  <label class="st-field">
    <span class="st-field-label">Auto-add new files</span>
    <select
      class="st-control narrow"
      value={autoIngest ? "true" : "false"}
      onchange={(e) =>
        onAutoIngest((e.currentTarget as HTMLSelectElement).value === "true")}
    >
      <option value="true">Enabled</option>
      <option value="false">Disabled</option>
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
    <p class="st-card-sub" style="margin-bottom: 0.75rem">
      Changing provider or model requires re-ingest.
    </p>
    <div class="st-field-grid">
      <label class="st-field">
        <span class="st-field-label">Embedding provider</span>
        <select
          class="st-control"
          value={settingsForm.EMBEDDING_PROVIDER}
          onchange={onEmbedProvider}
          disabled={saving}
        >
          <option value="fastembed">Bundled local (fastembed) — recommended</option>
          <option value="ollama">Ollama (optional)</option>
          <option value="openai_compatible">Cloud (OpenAI-compatible)</option>
        </select>
      </label>
      <label class="st-field">
        <span class="st-field-label">Embedding model</span>
        <input
          class="st-control"
          value={settingsForm.EMBEDDING_MODEL}
          placeholder={settingsForm.EMBEDDING_PROVIDER === "ollama"
            ? "nomic-embed-text"
            : settingsForm.EMBEDDING_PROVIDER === "openai_compatible"
              ? "text-embedding-3-small"
              : "BAAI/bge-small-en-v1.5"}
          disabled={saving}
          onblur={(e) =>
            onPersist({ EMBEDDING_MODEL: (e.currentTarget as HTMLInputElement).value })}
        />
      </label>
      <label class="st-field st-field-span">
        <span class="st-field-label">Ollama URL <span class="st-opt">chat or ollama embeds</span></span>
        <input
          class="st-control"
          value={settingsForm.OLLAMA_BASE_URL}
          placeholder="http://localhost:11434"
          disabled={saving}
          onblur={(e) =>
            onPersist({ OLLAMA_BASE_URL: (e.currentTarget as HTMLInputElement).value })}
        />
      </label>
    </div>
  </section>
{/if}

<style>
  .embed-warn {
    font-size: var(--text-sm);
    color: var(--warning, #b45309);
    background: var(--warning-dim, rgba(180, 83, 9, 0.08));
    border-radius: var(--radius-md, 8px);
    padding: 0.65rem 0.75rem;
    margin: 0;
    line-height: 1.45;
  }

  .embed-ok {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin: 0;
  }

  .linkish {
    background: none;
    border: none;
    color: var(--accent-link);
    font-size: inherit;
    cursor: pointer;
    padding: 0;
    margin-left: 0.35rem;
    text-decoration: underline;
  }
</style>
