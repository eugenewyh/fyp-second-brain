<script lang="ts">
  import type { ResearchResult } from "$lib/api";
  import { renderReport } from "$lib/research/render";
  import { saveResearchAsNote } from "$lib/vault/notes";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";

  interface Props {
    result: ResearchResult;
  }

  let { result }: Props = $props();
  let saving = $state(false);
  let saveMessage = $state("");

  async function saveAsNote() {
    saving = true;
    saveMessage = "";
    try {
      const path = await saveResearchAsNote(result);
      workspace.requestVaultRefresh();
      tabs.openNoteTab(path);
      workspace.setActiveNote(path);
      saveMessage = "Saved to vault";
    } catch (e) {
      saveMessage = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }
</script>

<div class="report-actions">
  <button class="btn-secondary" onclick={saveAsNote} disabled={saving}>
    {saving ? "Saving…" : "Save as note"}
  </button>
  {#if saveMessage}
    <span class="save-msg">{saveMessage}</span>
  {/if}
</div>
<div class="report report-content">
  {@html renderReport(result.report)}
</div>

<style>
  .report-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .save-msg {
    font-size: 0.8rem;
    color: var(--success);
  }

  .report {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 1rem 1.15rem;
    line-height: 1.6;
    max-height: 65vh;
    overflow-y: auto;
    font-size: 0.875rem;
  }
</style>