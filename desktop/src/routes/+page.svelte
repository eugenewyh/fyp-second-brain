<script lang="ts">
  import { onMount } from "svelte";
  import { api, waitForSidecar, type ResearchResult, type Settings } from "$lib/api";
  import { runResearchQuery } from "$lib/research/run";
  import CommandBar from "$lib/components/workspace/CommandBar.svelte";
  import WorkspaceShell from "$lib/components/workspace/WorkspaceShell.svelte";
  import VaultSidebar from "$lib/components/workspace/VaultSidebar.svelte";
  import InspectorPanel from "$lib/components/workspace/InspectorPanel.svelte";
  import ResearchCenter from "$lib/components/workspace/ResearchCenter.svelte";
  import LegacyPanels from "$lib/components/legacy/LegacyPanels.svelte";

  type WorkspaceMode = "research" | "query" | "documents" | "settings";

  let workspaceMode = $state<WorkspaceMode>("research");
  let connected = $state(false);
  let connectionError = $state("");
  let collectionCount = $state(0);

  let leftWidth = $state(260);
  let rightWidth = $state(300);

  let researchQuery = $state("");
  let researchLoading = $state(false);
  let researchResult = $state<ResearchResult | null>(null);
  let showDetails = $state(false);

  let quickQuestion = $state("");
  let quickLoading = $state(false);
  let quickAnswer = $state("");
  let quickSources = $state<{ index: number; source: string; page: number | null }[]>([]);

  let chatMessage = $state("");
  let chatResponse = $state("");

  let ingestPath = $state("");
  let ingestLoading = $state(false);
  let ingestMessage = $state("");

  let settings = $state<Settings | null>(null);
  let settingsForm = $state<Record<string, string>>({});
  let settingsSaving = $state(false);
  let settingsMessage = $state("");

  let fuzzyQuery = $state("");
  let semanticQuery = $state("");

  async function refreshStatus() {
    try {
      const status = await api.status();
      collectionCount = status.collection_count;
      connected = true;
      connectionError = "";
    } catch (e) {
      connected = false;
      connectionError = e instanceof Error ? e.message : "Sidecar unreachable";
    }
  }

  async function connect() {
    connectionError = "";
    const ready = await waitForSidecar();
    if (!ready) {
      connectionError = "Sidecar failed to start. Check that .venv exists and Ollama is running.";
      return;
    }
    await refreshStatus();
    if (workspaceMode === "settings") await loadSettings();
  }

  async function runResearch() {
    if (!researchQuery.trim()) return;
    workspaceMode = "research";
    researchLoading = true;
    researchResult = null;
    const outcome = await runResearchQuery(researchQuery);
    researchResult = outcome.result;
    if (outcome.error) {
      connectionError = outcome.error;
    } else {
      connectionError = "";
      await refreshStatus();
    }
    researchLoading = false;
  }

  async function runQuickQuery() {
    if (!quickQuestion.trim()) return;
    quickLoading = true;
    quickAnswer = "";
    quickSources = [];
    try {
      const result = await api.query(quickQuestion.trim());
      quickAnswer = result.answer;
      quickSources = result.sources;
    } catch (e) {
      quickAnswer = e instanceof Error ? e.message : "Query failed";
    } finally {
      quickLoading = false;
    }
  }

  async function runInspectorChat(message: string) {
    chatMessage = message;
    quickQuestion = message;
    quickLoading = true;
    chatResponse = "";
    try {
      const result = await api.query(message);
      chatResponse = result.answer;
      quickSources = result.sources;
    } catch (e) {
      chatResponse = e instanceof Error ? e.message : "Query failed";
    } finally {
      quickLoading = false;
    }
  }

  async function runIngest() {
    if (!ingestPath.trim()) return;
    ingestLoading = true;
    ingestMessage = "";
    try {
      const result = await api.ingest(ingestPath.trim());
      ingestMessage = `Ingested ${result.ingested_chunks} chunks. Total: ${result.collection_total}`;
      await refreshStatus();
    } catch (e) {
      ingestMessage = e instanceof Error ? e.message : "Ingest failed";
    } finally {
      ingestLoading = false;
    }
  }

  async function loadSettings() {
    settings = await api.getSettings();
    settingsForm = { ...settings.values };
  }

  async function saveSettings() {
    settingsSaving = true;
    settingsMessage = "";
    try {
      await api.updateSettings(settingsForm);
      settingsMessage = "Settings saved.";
      await loadSettings();
    } catch (e) {
      settingsMessage = e instanceof Error ? e.message : "Save failed";
    } finally {
      settingsSaving = false;
    }
  }

  function setWorkspaceMode(mode: WorkspaceMode) {
    workspaceMode = mode;
    if (mode === "settings" && connected) loadSettings();
  }

  onMount(() => {
    connect();
  });
</script>

<div class="app" data-testid="second-brain-app">
  <CommandBar
    bind:query={researchQuery}
    {connected}
    loading={researchLoading}
    onSubmit={runResearch}
    onLegacyMode={setWorkspaceMode}
    activeLegacyMode={workspaceMode}
  />

  <WorkspaceShell bind:leftWidth bind:rightWidth>
    {#snippet left()}
      <VaultSidebar
        {collectionCount}
        {connected}
        {connectionError}
        onRetry={connect}
        bind:fuzzyQuery
        bind:semanticQuery
      />
    {/snippet}

    {#snippet center()}
      <div class="center-workspace">
        <ResearchCenter
          bind:query={researchQuery}
          {connected}
          bind:loading={researchLoading}
          bind:result={researchResult}
          bind:showDetails
          onRun={runResearch}
          hidden={workspaceMode !== "research"}
        />
        {#if workspaceMode !== "research"}
          <LegacyPanels
            mode={workspaceMode}
            {connected}
            bind:quickQuestion
            {quickLoading}
            {quickAnswer}
            {quickSources}
            bind:ingestPath
            {ingestLoading}
            {ingestMessage}
            {settings}
            bind:settingsForm
            {settingsSaving}
            {settingsMessage}
            onQuickQuestionChange={(v) => (quickQuestion = v)}
            onRunQuickQuery={runQuickQuery}
            onIngestPathChange={(v) => (ingestPath = v)}
            onRunIngest={runIngest}
            onSettingsFormChange={(v) => (settingsForm = v)}
            onSaveSettings={saveSettings}
          />
        {/if}
      </div>
    {/snippet}

    {#snippet right()}
      <InspectorPanel
        bind:chatMessage
        chatResponse={chatResponse}
        chatLoading={quickLoading}
        onChatSend={runInspectorChat}
        {researchResult}
        {researchLoading}
        {quickSources}
      />
    {/snippet}
  </WorkspaceShell>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .center-workspace {
    height: 100%;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
</style>