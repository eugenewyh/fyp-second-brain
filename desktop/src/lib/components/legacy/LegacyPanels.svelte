<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import type { Settings } from "$lib/api";

  type LegacyMode = "query" | "documents" | "settings";

  interface Props {
    mode: LegacyMode;
    connected: boolean;
    quickQuestion: string;
    quickLoading: boolean;
    quickAnswer: string;
    quickSources: { index: number; source: string; page: number | null }[];
    ingestPath: string;
    ingestLoading: boolean;
    ingestMessage: string;
    settings: Settings | null;
    settingsForm: Record<string, string>;
    settingsSaving: boolean;
    settingsMessage: string;
    onQuickQuestionChange: (v: string) => void;
    onRunQuickQuery: () => void;
    onIngestPathChange: (v: string) => void;
    onRunIngest: () => void;
    onSettingsFormChange: (v: Record<string, string>) => void;
    onSaveSettings: () => void;
  }

  let {
    mode,
    connected,
    quickQuestion = $bindable(""),
    quickLoading,
    quickAnswer,
    quickSources,
    ingestPath = $bindable(""),
    ingestLoading,
    ingestMessage,
    settings,
    settingsForm = $bindable({}),
    settingsSaving,
    settingsMessage,
    onQuickQuestionChange,
    onRunQuickQuery,
    onIngestPathChange,
    onRunIngest,
    onSettingsFormChange,
    onSaveSettings,
  }: Props = $props();

  async function pickFolder() {
    const selected = await open({ directory: true, multiple: false });
    if (selected && typeof selected === "string") {
      ingestPath = selected;
      onIngestPathChange(selected);
    }
  }
</script>

<section class="legacy-panel" data-testid="legacy-panel">
  {#if mode === "query"}
    <h2>Quick Query</h2>
    <p class="hint">Fast RAG lookup against your personal knowledge base</p>
    <div class="input-row">
      <input
        bind:value={quickQuestion}
        oninput={() => onQuickQuestionChange(quickQuestion)}
        placeholder="Ask a question…"
      />
    </div>
    <button class="btn-primary" onclick={onRunQuickQuery} disabled={quickLoading || !connected}>
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

  {:else if mode === "documents"}
    <h2>Ingest Documents</h2>
    <p class="hint">Add PDF, TXT, or MD files from a folder into your knowledge base</p>
    <div class="input-row folder-row">
      <input
        bind:value={ingestPath}
        oninput={() => onIngestPathChange(ingestPath)}
        placeholder="/path/to/your/documents"
      />
      <button class="btn-secondary" onclick={pickFolder}>Browse</button>
    </div>
    <button class="btn-primary" onclick={onRunIngest} disabled={ingestLoading || !connected}>
      {ingestLoading ? "Ingesting…" : "Ingest Folder"}
    </button>
    {#if ingestMessage}
      <p class="message">{ingestMessage}</p>
    {/if}
    <div class="info-card">
      <p>Default folder: <code>data/documents/</code> in project root</p>
      <p>Supported: .pdf, .txt, .md</p>
    </div>

  {:else if mode === "settings"}
    <h2>Settings</h2>
    <p class="hint">Configure Ollama, Tavily, and retrieval options</p>
    {#if settings}
      <div class="settings-grid">
        <label>
          Ollama URL
          <input
            bind:value={settingsForm.OLLAMA_BASE_URL}
            oninput={() => onSettingsFormChange(settingsForm)}
          />
        </label>
        <label>
          Embedding Model
          <input
            bind:value={settingsForm.EMBEDDING_MODEL}
            oninput={() => onSettingsFormChange(settingsForm)}
          />
        </label>
        <label>
          LLM Model
          <input
            bind:value={settingsForm.LLM_MODEL}
            oninput={() => onSettingsFormChange(settingsForm)}
          />
        </label>
        <label>
          Tavily API Key
          <input
            type="password"
            bind:value={settingsForm.TAVILY_API_KEY}
            oninput={() => onSettingsFormChange(settingsForm)}
            placeholder="tvly-…"
          />
        </label>
        <label>
          Enable Web Search
          <select
            bind:value={settingsForm.ENABLE_WEB_SEARCH}
            onchange={() => onSettingsFormChange(settingsForm)}
          >
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>
        <label>
          Enable arXiv
          <select
            bind:value={settingsForm.ENABLE_ARXIV}
            onchange={() => onSettingsFormChange(settingsForm)}
          >
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>
        <label>
          Max Revisions
          <input
            bind:value={settingsForm.MAX_REVISIONS}
            oninput={() => onSettingsFormChange(settingsForm)}
          />
        </label>
      </div>
      <div class="actions">
        <button class="btn-primary" onclick={onSaveSettings} disabled={settingsSaving}>
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
  {/if}
</section>

<style>
  .legacy-panel {
    padding: 1.25rem 1.5rem;
    height: 100%;
    overflow-y: auto;
  }

  .legacy-panel h2 {
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