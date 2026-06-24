<script lang="ts">
  import { onMount } from "svelte";
  import { open } from "@tauri-apps/plugin-dialog";
  import { api, waitForSidecar, type ResearchResult, type Settings } from "$lib/api";

  type Tab = "research" | "query" | "documents" | "settings";

  let activeTab = $state<Tab>("research");
  let connected = $state(false);
  let connectionError = $state("");
  let collectionCount = $state(0);

  let researchQuery = $state("");
  let researchLoading = $state(false);
  let researchResult = $state<ResearchResult | null>(null);
  let showDetails = $state(false);

  let quickQuestion = $state("");
  let quickLoading = $state(false);
  let quickAnswer = $state("");
  let quickSources = $state<{ index: number; source: string; page: number | null }[]>([]);

  let ingestPath = $state("");
  let ingestLoading = $state(false);
  let ingestMessage = $state("");

  let settings = $state<Settings | null>(null);
  let settingsForm = $state<Record<string, string>>({});
  let settingsSaving = $state(false);
  let settingsMessage = $state("");

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "research", label: "Research", icon: "🔬" },
    { id: "query", label: "Quick Query", icon: "💬" },
    { id: "documents", label: "Documents", icon: "📁" },
    { id: "settings", label: "Settings", icon: "⚙️" },
  ];

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
    if (activeTab === "settings") await loadSettings();
  }

  async function runResearch() {
    if (!researchQuery.trim()) return;
    researchLoading = true;
    researchResult = null;
    try {
      researchResult = await api.research(researchQuery.trim());
      await refreshStatus();
    } catch (e) {
      connectionError = e instanceof Error ? e.message : "Research failed";
    } finally {
      researchLoading = false;
    }
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

  function renderReport(md: string): string {
    return md
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/^(.+)$/gm, (line) => {
        if (line.startsWith('<h2>') || line.startsWith('<li>')) return line;
        return line;
      });
  }

  onMount(() => {
    connect();
  });

  $effect(() => {
    if (activeTab === "settings" && connected) loadSettings();
  });
</script>

<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <h1>Second Brain</h1>
      <p class="subtitle">FYP · TP068819</p>
    </div>

    <nav>
      {#each tabs as tab}
        <button
          class="nav-item"
          class:active={activeTab === tab.id}
          onclick={() => (activeTab = tab.id)}
        >
          <span class="nav-icon">{tab.icon}</span>
          {tab.label}
        </button>
      {/each}
    </nav>

    <div class="status-bar">
      <span class="status-dot" class:online={connected}></span>
      {connected ? `${collectionCount} chunks indexed` : "Disconnected"}
      {#if connectionError}
        <p class="error-text">{connectionError}</p>
        <button class="btn-secondary retry-btn" onclick={connect}>Retry</button>
      {/if}
    </div>
  </aside>

  <main class="content">
    {#if activeTab === "research"}
      <section class="panel">
        <h2>Autonomous Research</h2>
        <p class="hint">Multi-agent workflow: planner → retriever → analyst → verifier → synthesizer</p>

        <div class="input-row">
          <textarea
            bind:value={researchQuery}
            placeholder="e.g. What are servlets in Java and how do they compare to modern frameworks?"
            rows="3"
          ></textarea>
        </div>
        <div class="actions">
          <button class="btn-primary" onclick={runResearch} disabled={researchLoading || !connected}>
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
          <div class="report report-content">
            {@html renderReport(researchResult.report)}
          </div>
        {/if}
      </section>

    {:else if activeTab === "query"}
      <section class="panel">
        <h2>Quick Query</h2>
        <p class="hint">Fast RAG lookup against your personal knowledge base</p>

        <div class="input-row">
          <input bind:value={quickQuestion} placeholder="Ask a question…" />
        </div>
        <button class="btn-primary" onclick={runQuickQuery} disabled={quickLoading || !connected}>
          {quickLoading ? "Searching…" : "Ask"}
        </button>

        {#if quickAnswer}
          <div class="answer-box">
            <h3>Answer</h3>
            <p>{quickAnswer}</p>
            {#if quickSources.length}
              <h3>Sources</h3>
              <ul>
                {#each quickSources as src}
                  <li>[{src.index}] {src.source}{src.page ? `, p.${src.page}` : ""}</li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}
      </section>

    {:else if activeTab === "documents"}
      <section class="panel">
        <h2>Ingest Documents</h2>
        <p class="hint">Add PDF, TXT, or MD files from a folder into your knowledge base</p>

        <div class="input-row folder-row">
          <input bind:value={ingestPath} placeholder="/path/to/your/documents" />
          <button class="btn-secondary" onclick={pickFolder}>Browse</button>
        </div>
        <button class="btn-primary" onclick={runIngest} disabled={ingestLoading || !connected}>
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

    {:else if activeTab === "settings"}
      <section class="panel">
        <h2>Settings</h2>
        <p class="hint">Configure Ollama, Tavily, and retrieval options</p>

        {#if settings}
          <div class="settings-grid">
            <label>
              Ollama URL
              <input bind:value={settingsForm.OLLAMA_BASE_URL} />
            </label>
            <label>
              Embedding Model
              <input bind:value={settingsForm.EMBEDDING_MODEL} />
            </label>
            <label>
              LLM Model
              <input bind:value={settingsForm.LLM_MODEL} />
            </label>
            <label>
              Tavily API Key
              <input type="password" bind:value={settingsForm.TAVILY_API_KEY} placeholder="tvly-…" />
            </label>
            <label>
              Enable Web Search
              <select bind:value={settingsForm.ENABLE_WEB_SEARCH}>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
            <label>
              Enable arXiv
              <select bind:value={settingsForm.ENABLE_ARXIV}>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
            <label>
              Max Revisions
              <input bind:value={settingsForm.MAX_REVISIONS} />
            </label>
          </div>

          <div class="actions">
            <button class="btn-primary" onclick={saveSettings} disabled={settingsSaving}>
              {settingsSaving ? "Saving…" : "Save Settings"}
            </button>
          </div>
          {#if settingsMessage}
            <p class="message">{settingsMessage}</p>
          {/if}
          <p class="hint">
            Tavily: {settings.tavily_configured ? "configured" : "not set — web search disabled"}
          </p>
        {:else if connected}
          <div class="loading">Loading settings…</div>
        {/if}
      </section>
    {/if}
  </main>
</div>

<style>
  .app {
    display: flex;
    height: 100vh;
  }

  .sidebar {
    width: 220px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 1.25rem 0.75rem;
  }

  .brand h1 {
    font-size: 1.15rem;
    font-weight: 700;
    padding: 0 0.5rem;
  }

  .subtitle {
    font-size: 0.75rem;
    color: var(--text-muted);
    padding: 0.2rem 0.5rem 1.25rem;
  }

  nav {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 1;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.65rem 0.75rem;
    background: transparent;
    color: var(--text-muted);
    text-align: left;
    font-size: 0.9rem;
  }

  .nav-item:hover {
    background: var(--surface-hover);
    color: var(--text);
  }

  .nav-item.active {
    background: var(--accent);
    color: white;
  }

  .nav-icon {
    font-size: 1rem;
  }

  .status-bar {
    font-size: 0.75rem;
    color: var(--text-muted);
    padding: 0.75rem 0.5rem 0;
    border-top: 1px solid var(--border);
  }

  .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--error);
    margin-right: 0.4rem;
  }

  .status-dot.online {
    background: var(--success);
  }

  .error-text {
    color: var(--error);
    margin-top: 0.4rem;
    font-size: 0.7rem;
  }

  .retry-btn {
    margin-top: 0.5rem;
    width: 100%;
    font-size: 0.75rem;
    padding: 0.4rem;
  }

  .content {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
  }

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

  .answer-box {
    margin-top: 1.25rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
  }

  .answer-box h3 {
    font-size: 0.9rem;
    color: var(--accent);
    margin-bottom: 0.5rem;
  }

  .answer-box ul {
    margin-top: 0.5rem;
    padding-left: 1.2rem;
    color: var(--text-muted);
    font-size: 0.85rem;
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

  .settings-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.25rem;
  }

  .settings-grid label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: var(--text-muted);
  }
</style>