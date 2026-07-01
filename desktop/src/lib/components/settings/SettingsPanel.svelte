<script lang="ts">
  import { api, type Settings } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { loadAutoIngestEnabled, saveAutoIngestEnabled } from "$lib/vault/watcher-prefs";
  import Panel from "$lib/ui/Panel.svelte";
  import Button from "$lib/ui/Button.svelte";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";

  let settings = $state<Settings | null>(null);
  let settingsForm = $state<Record<string, string>>({});
  let settingsSaving = $state(false);
  let settingsMessage = $state("");
  let autoIngest = $state(loadAutoIngestEnabled());

  async function loadSettings() {
    settings = await api.getSettings();
    settingsForm = { ...settings.values };
  }

  async function saveSettings() {
    settingsSaving = true;
    settingsMessage = "";
    try {
      await api.updateSettings(settingsForm);
      settingsMessage = "Saved";
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

<Panel title="Settings" description="Ollama, retrieval, and vault options">
  {#if settings}
    <div class="section">
      <SectionLabel>Models</SectionLabel>
      <div class="settings-grid">
        <label>Ollama URL <input bind:value={settingsForm.OLLAMA_BASE_URL} /></label>
        <label>Embedding model <input bind:value={settingsForm.EMBEDDING_MODEL} /></label>
        <label>LLM model <input bind:value={settingsForm.LLM_MODEL} /></label>
      </div>
    </div>

    <div class="section">
      <SectionLabel>Retrieval</SectionLabel>
      <div class="settings-grid">
        <label>
          Web search
          <select bind:value={settingsForm.ENABLE_WEB_SEARCH}>
            <option value="true">On</option>
            <option value="false">Off</option>
          </select>
        </label>
        <label>
          arXiv
          <select bind:value={settingsForm.ENABLE_ARXIV}>
            <option value="true">On</option>
            <option value="false">Off</option>
          </select>
        </label>
        <label>Max revisions <input bind:value={settingsForm.MAX_REVISIONS} /></label>
        <label>
          Tavily key
          <input type="password" bind:value={settingsForm.TAVILY_API_KEY} placeholder="tvly-…" />
        </label>
      </div>
    </div>

    <div class="section">
      <SectionLabel>Vault</SectionLabel>
      <label>
        Auto-ingest on file changes
        <select
          value={autoIngest ? "true" : "false"}
          onchange={(e) => {
            autoIngest = (e.currentTarget as HTMLSelectElement).value === "true";
            saveAutoIngestEnabled(autoIngest);
          }}
        >
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      </label>
    </div>

    <Button variant="primary" onclick={saveSettings} disabled={settingsSaving}>
      {settingsSaving ? "Saving…" : "Save"}
    </Button>
    {#if settingsMessage}
      <p class="message">{settingsMessage}</p>
    {/if}
    <p class="meta">
      Tavily: {settings.tavily_configured ? "configured" : "not set"}
    </p>
  {:else if connection.connected}
    <p class="ui-empty">Loading…</p>
  {/if}
</Panel>

<style>
  .section {
    margin-bottom: 1.25rem;
  }

  .section :global(.section-label) {
    display: block;
    margin-bottom: 0.5rem;
  }

  .settings-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.75rem;
    color: var(--text-faint);
  }

  .message {
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--success);
  }

  .meta {
    margin-top: 0.5rem;
    font-size: 0.7rem;
    color: var(--text-faint);
    font-family: var(--font-mono);
  }
</style>