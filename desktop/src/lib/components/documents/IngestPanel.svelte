<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { api } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import Panel from "$lib/ui/Panel.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { FolderOpen } from "@lucide/svelte";

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
      ingestMessage = `Ingested ${result.ingested_chunks} chunks · ${result.collection_total} total`;
      await connection.refreshStatus();
      workspace.requestVaultRefresh();
    } catch (e) {
      ingestMessage = e instanceof Error ? e.message : "Ingest failed";
    } finally {
      ingestLoading = false;
    }
  }
</script>

<Panel title="Ingest" description="Add PDF, TXT, or MD files to your knowledge base">
  <div class="drop-zone">
    <FolderOpen size={24} strokeWidth={1.5} />
    <p>Select a folder to index into Chroma</p>
    <div class="folder-row">
      <input bind:value={ingestPath} placeholder="Path to documents…" />
      <Button variant="secondary" onclick={pickFolder}>Browse</Button>
    </div>
    <Button
      variant="primary"
      onclick={runIngest}
      disabled={ingestLoading || !connection.connected}
    >
      {ingestLoading ? "Ingesting…" : "Ingest folder"}
    </Button>
  </div>

  {#if ingestMessage}
    <p class="message">{ingestMessage}</p>
  {/if}

  <p class="meta">Default: <code>data/documents/</code> · Supports .pdf .txt .md</p>
</Panel>

<style>
  .drop-zone {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.65rem;
    padding: 1.25rem;
    background: var(--surface);
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    text-align: center;
    color: var(--text-faint);
    font-size: 0.75rem;
  }

  .drop-zone :global(svg) {
    color: var(--text-muted);
  }

  .folder-row {
    display: flex;
    gap: 0.5rem;
    width: 100%;
    max-width: 420px;
  }

  .folder-row input {
    flex: 1;
    text-align: left;
  }

  .message {
    margin-top: 0.75rem;
    font-size: 0.75rem;
    color: var(--success);
  }

  .meta {
    margin-top: 0.75rem;
    font-size: 0.7rem;
    color: var(--text-faint);
    font-family: var(--font-mono);
  }

  .meta code {
    color: var(--text-muted);
  }
</style>