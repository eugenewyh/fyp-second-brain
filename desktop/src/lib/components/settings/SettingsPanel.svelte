<script lang="ts">
  import { api, type Settings } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";

  let settings = $state<Settings | null>(null);
  let settingsForm = $state<Record<string, string>>({});
  let settingsSaving = $state(false);
  let settingsMessage = $state("");

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

  $effect(() => {
    if (tabs.activeTab?.type === "settings" && connection.connected) {
      loadSettings();
    }
  });
</script>

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
  {:else if connection.connected}
    <div class="loading">Loading settings…</div>
  {/if}
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

  .actions {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }

  .message {
    color: var(--success);
    margin-bottom: 0.5rem;
  }

  .loading {
    color: var(--warning);
    padding: 1rem;
    background: var(--surface);
    border-radius: var(--radius);
  }
</style>