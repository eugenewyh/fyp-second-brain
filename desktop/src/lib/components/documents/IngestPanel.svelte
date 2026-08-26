<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { api } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { app } from "$lib/stores/app.svelte";
  import Panel from "$lib/ui/Panel.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { FolderOpen } from "@lucide/svelte";

  let ingestPath = $state("");
  let ingestLoading = $state(false);
  let ingestMessage = $state("");
  let ingestError = $state(false);
  let localSuggestions = $state<string[]>([]);
  let resetIndex = $state(false);

  $effect(() => {
    if (connection.reindexRequired || !connection.embeddingsOk) {
      resetIndex = true;
    }
  });

  async function pickFolder() {
    const selected = await open({ directory: true, multiple: false });
    if (selected && typeof selected === "string") {
      ingestPath = selected;
    }
  }

  async function runIngest() {
    if (!ingestPath.trim()) return;
    ingestLoading = true;
    ingestMessage = "";
    ingestError = false;
    localSuggestions = [];
    try {
      const result = await api.ingest(ingestPath.trim(), { reset: resetIndex });
      const n = result.ingested_chunks;
      ingestMessage =
        n === 1
          ? `1 page added — indexing complete (${result.collection_total} total in library)`
          : `${n} pages added — indexing complete (${result.collection_total} total in library)`;
      if (result.reset) {
        ingestMessage += " · index was reset";
      }
      const suggestions = result.suggestions ?? [];
      localSuggestions = suggestions;
      assistant.setIngestSuggestions(suggestions);
      await connection.refreshStatus();
      workspace.requestVaultRefresh();
    } catch (e) {
      ingestMessage = e instanceof Error ? e.message : "Couldn't add documents";
      ingestError = true;
    } finally {
      ingestLoading = false;
    }
  }

  function researchSuggestion(prompt: string) {
    app.closeSheet();
    app.openAgent();
    void assistant.runResearch(null, prompt);
  }
</script>

<Panel title="Add documents" description="Index PDFs, text, or notes into your personal library">
  <div class="ingest-zone">
    <FolderOpen size={28} strokeWidth={1.5} />
    <p class="title">Choose a folder to add</p>
    <p class="desc">Your files stay on this device. We'll index them for search and research.</p>
    <div class="folder-row">
      <input bind:value={ingestPath} placeholder="Path to documents…" />
      <Button variant="secondary" onclick={pickFolder}>Browse</Button>
    </div>
    <label class="reset-row">
      <input type="checkbox" bind:checked={resetIndex} />
      <span>Reset knowledge index first (fixes corrupt search / embedding changes)</span>
    </label>
    <Button
      variant="primary"
      onclick={runIngest}
      disabled={ingestLoading || !connection.connected || !ingestPath.trim()}
    >
      {ingestLoading ? "Adding…" : "Add folder"}
    </Button>
  </div>

  {#if ingestMessage}
    <p class="message" class:error={ingestError}>{ingestMessage}</p>
  {/if}

  {#if localSuggestions.length && !ingestError}
    <div class="suggest">
      <p class="suggest-title">Suggested research (from new files)</p>
      <ul>
        {#each localSuggestions as s}
          <li>
            <button type="button" class="suggest-btn" onclick={() => researchSuggestion(s)}>
              {s}
            </button>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <p class="meta">Supports PDF, text, and markdown · Default folder: <code>data/documents/</code></p>
</Panel>

<style>
  .ingest-zone {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.65rem;
    padding: var(--space-4) 0;
    background: transparent;
    border: none;
    border-top: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
    text-align: left;
    color: var(--text-faint);
    font-size: var(--text-sm);
  }

  .ingest-zone :global(svg) {
    color: var(--text-faint);
    display: none;
  }

  .title {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    color: var(--text);
  }

  .desc {
    font-size: var(--text-xs);
    color: var(--text-faint);
    max-width: 22rem;
    line-height: 1.45;
  }

  .folder-row {
    display: flex;
    gap: 0.5rem;
    width: 100%;
    max-width: 28rem;
  }

  .reset-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    max-width: 28rem;
    margin: 0.65rem 0 0.25rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    text-align: left;
    cursor: pointer;
  }

  .reset-row input {
    margin-top: 0.2rem;
  }

  .message {
    margin-top: 0.75rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .message.error {
    color: var(--text);
  }

  .meta {
    margin-top: 0.75rem;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .meta code {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
  }

  .suggest {
    margin-top: var(--space-4);
    border-top: 1px solid var(--border-subtle);
    padding-top: var(--space-3);
  }

  .suggest-title {
    font-size: var(--text-xs);
    color: var(--text-faint);
    margin-bottom: var(--space-2);
  }

  .suggest ul {
    list-style: none;
  }

  .suggest-btn {
    width: 100%;
    text-align: left;
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border-subtle);
    border-radius: 0;
  }

  .suggest-btn:hover {
    color: var(--text);
  }
</style>
