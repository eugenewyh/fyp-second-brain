<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { api } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";

  let ingestPath = $state("");
  let ingestLoading = $state(false);
  let ingestMessage = $state("");

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
    try {
      const result = await api.ingest(ingestPath.trim());
      ingestMessage = `Ingested ${result.ingested_chunks} chunks. Total: ${result.collection_total}`;
      await connection.refreshStatus();
      workspace.requestVaultRefresh();
    } catch (e) {
      ingestMessage = e instanceof Error ? e.message : "Ingest failed";
    } finally {
      ingestLoading = false;
    }
  }
</script>

<section class="panel">
  <h2>Ingest Documents</h2>
  <p class="hint">Add PDF, TXT, or MD files from a folder into your knowledge base</p>

  <div class="input-row folder-row">
    <input bind:value={ingestPath} placeholder="/path/to/your/documents" />
    <button class="btn-secondary" onclick={pickFolder}>Browse</button>
  </div>
  <button class="btn-primary" onclick={runIngest} disabled={ingestLoading || !connection.connected}>
    {ingestLoading ? "Ingesting…" : "Ingest Folder"}
  </button>

  {#if ingestMessage}
    <p class="message">{ingestMessage}</p>
  {/if}

  <div class="info-card">
    <p>Default folder: <code>data/documents/</code> in project root</p>
    <p>Supported: .pdf, .txt, .md</p>
  </div>
</section>

<style>
  .panel h2 {
    font-size: 1.4rem;
    margin-bottom: 0.25rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 1.25rem;
  }

  .input-row {
    margin-bottom: 0.75rem;
  }

  .folder-row {
    display: flex;
    gap: 0.5rem;
  }

  .folder-row input {
    flex: 1;
  }

  .message {
    margin-top: 1rem;
    color: var(--success);
  }

  .info-card {
    margin-top: 1.5rem;
    padding: 1rem;
    background: var(--surface);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .info-card code {
    color: var(--accent);
  }
</style>