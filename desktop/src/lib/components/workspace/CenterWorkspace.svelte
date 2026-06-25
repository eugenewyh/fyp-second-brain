<script lang="ts">
  import { tabs } from "$lib/stores/tabs.svelte";
  import TabBar from "./TabBar.svelte";
  import ResearchPanel from "$lib/components/research/ResearchPanel.svelte";
  import QuickQueryPanel from "$lib/components/query/QuickQueryPanel.svelte";
  import IngestPanel from "$lib/components/documents/IngestPanel.svelte";
  import SettingsPanel from "$lib/components/settings/SettingsPanel.svelte";
  import NoteEditor from "$lib/components/editor/NoteEditor.svelte";
  import PdfViewer from "$lib/components/editor/PdfViewer.svelte";
  import EditorPlaceholder from "$lib/components/editor/EditorPlaceholder.svelte";
  import { isPdfPath } from "$lib/vault/pdf";
</script>

<div class="center-workspace">
  <TabBar />
  <div class="center-content">
    {#if tabs.activeTab?.type === "research"}
      <ResearchPanel />
    {:else if tabs.activeTab?.type === "query"}
      <QuickQueryPanel />
    {:else if tabs.activeTab?.type === "ingest"}
      <IngestPanel />
    {:else if tabs.activeTab?.type === "settings"}
      <SettingsPanel />
    {:else if tabs.activeTab?.type === "note" && tabs.activeTab.path}
      {#if tabs.activeTab.path.endsWith(".md")}
        {#key tabs.activeTab.path}
          <NoteEditor path={tabs.activeTab.path} />
        {/key}
      {:else if isPdfPath(tabs.activeTab.path)}
        {#key tabs.activeTab.path}
          <PdfViewer path={tabs.activeTab.path} />
        {/key}
      {:else}
        <EditorPlaceholder path={tabs.activeTab.path} />
      {/if}
    {:else}
      <ResearchPanel />
    {/if}
  </div>
</div>

<style>
  .center-workspace {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    background: var(--bg);
  }

  .center-content {
    flex: 1;
    overflow-y: auto;
    padding: 1.25rem 1.5rem;
  }
</style>