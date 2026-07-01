<script lang="ts">
  import { tabs } from "$lib/stores/tabs.svelte";
  import { research } from "$lib/stores/research.svelte";
  import TabBar from "./TabBar.svelte";
  import WelcomePanel from "./WelcomePanel.svelte";
  import ResearchPanel from "$lib/components/research/ResearchPanel.svelte";
  import QuickQueryPanel from "$lib/components/query/QuickQueryPanel.svelte";
  import IngestPanel from "$lib/components/documents/IngestPanel.svelte";
  import SettingsPanel from "$lib/components/settings/SettingsPanel.svelte";
  import NoteEditor from "$lib/components/editor/NoteEditor.svelte";
  import PdfViewer from "$lib/components/editor/PdfViewer.svelte";
  import EditorPlaceholder from "$lib/components/editor/EditorPlaceholder.svelte";
  import { isPdfPath } from "$lib/vault/pdf";

  const showWelcome = $derived(
    tabs.activeTab?.type === "research" &&
      !research.query &&
      !research.result &&
      !research.loading,
  );

  const isNoteTab = $derived(tabs.activeTab?.type === "note");
</script>

<div class="center-workspace">
  <TabBar />
  <div class="center-content" class:flush={isNoteTab}>
    {#if tabs.activeTab?.type === "research"}
      {#if showWelcome}
        <WelcomePanel />
      {:else}
        <ResearchPanel />
      {/if}
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
      <WelcomePanel />
    {/if}
  </div>
</div>

<style>
  .center-workspace {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    background: var(--bg-elevated);
  }

  .center-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem 1.25rem;
  }

  .center-content.flush {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
</style>