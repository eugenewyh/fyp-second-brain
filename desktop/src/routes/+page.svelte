<script lang="ts">
  import { onMount } from "svelte";
  import { api, waitForSidecar, type ResearchResult, type Settings } from "$lib/api";
  import { renderReport } from "$lib/research/render";
  import { runResearchQuery } from "$lib/research/run";
  import CommandBar from "$lib/components/workspace/CommandBar.svelte";
  import WorkspaceShell from "$lib/components/workspace/WorkspaceShell.svelte";
  import VaultSidebar from "$lib/components/workspace/VaultSidebar.svelte";
  import InspectorPanel from "$lib/components/workspace/InspectorPanel.svelte";
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
    researchLoading = true;
    researchResult = null;
    workspaceMode = "research";
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
    onQueryChange={(v) => (researchQuery = v)}
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
      {#if workspaceMode === "research"}
        <!-- Legacy Research tab evolved into center workspace (markup preserved verbatim) -->
        <section class="panel research-panel" data-testid="research-workspace">
          <h2>Autonomous Research</h2>
          <p class="hint">Multi-agent workflow: planner → retriever → analyst → verifier → synthesizer</p>

          <div class="input-row">
            <textarea
              bind:value={researchQuery}
              placeholder="e.g. What are servlets in Java and how do they compare to modern frameworks?"
              rows="3"
              data-testid="research-query"
            ></textarea>
          </div>
          <div class="actions">
            <button
              class="btn-primary"
              onclick={runResearch}
              disabled={researchLoading || !connected}
              data-testid="run-research"
            >
              {researchLoading ? "Researching…" : "Run Research"}
            </button>
            {#if researchResult}
              <button class="btn-secondary" onclick={() => (showDetails = !showDetails)}>
                {showDetails ? "Hide details" : "Show details"}
              </button>
            {/if}
          </div>

          {#if researchLoading}
            <div class="loading">Running multi-agent pipeline… This may take 1–2 minutes.</div>
          {/if}

          {#if researchResult && showDetails}
            <div class="details">
              <h3>Plan</h3>
              <pre>{researchResult.plan}</pre>
              <h3>Retrieval</h3>
              <pre>{JSON.stringify(researchResult.retrieval_stats, null, 2)}</pre>
              {#if researchResult.retrieval_log.length}
                <pre>{researchResult.retrieval_log.join("\n")}</pre>
              {/if}
              {#if researchResult.revision_count}
                <p>Revisions: {researchResult.revision_count}</p>
              {/if}
            </div>
          {/if}

          {#if researchResult}
            <div class="report report-content" data-testid="research-report">
              {@html renderReport(researchResult.report)}
            </div>
          {/if}
        </section>
      {:else}
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

  .research-panel {
    padding: 1.25rem 1.5rem;
    height: 100%;
    overflow-y: auto;
  }

  .research-panel h2 {
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

  .actions {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
  }

  .loading {
    color: var(--warning);
    padding: 1rem;
    background: var(--surface);
    border-radius: var(--radius);
    margin-bottom: 1rem;
  }

  .report {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    line-height: 1.6;
    max-height: 60vh;
    overflow-y: auto;
  }

  .details {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-bottom: 1rem;
    font-size: 0.8rem;
  }

  .details pre {
    white-space: pre-wrap;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
  }

  .details h3 {
    font-size: 0.85rem;
    color: var(--accent);
    margin-bottom: 0.3rem;
  }
</style>