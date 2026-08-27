<script lang="ts">
  import { api, type Settings } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { app } from "$lib/stores/app.svelte";
  import ModelsPage from "./ModelsPage.svelte";
  import AppearancePage from "./AppearancePage.svelte";
  import AccountPage from "./AccountPage.svelte";
  import "./settings.css";

  import {
    GROQ_DEFAULT_MODEL,
    GROQ_FALLBACK_MODEL,
    LLM_PROVIDERS,
    type LlmProviderId,
    isProviderConnected,
    modelHint,
    modelsForProvider,
    providerMeta,
    resolveModelForProvider,
  } from "$lib/llm/models";

  type SettingsTab = "appearance" | "models" | "account";

  const TABS: { id: SettingsTab; label: string }[] = [
    { id: "appearance", label: "Appearance" },
    { id: "models", label: "Models" },
    { id: "account", label: "Account" },
  ];

  let settings = $state<Settings | null>(null);
  let settingsForm = $state<Record<string, string>>({});
  let settingsSaving = $state(false);
  let settingsMessage = $state("");
  let settingsError = $state(false);
  let tab = $state<SettingsTab>(
    app.settingsTab === "account" || app.settingsTab === "models" || app.settingsTab === "appearance"
      ? app.settingsTab
      : "appearance",
  );

  $effect(() => {
    if (app.settingsTab === "account" || app.settingsTab === "models" || app.settingsTab === "appearance") {
      tab = app.settingsTab;
    }
  });
  let reloading = $state(false);

  let modalOpen = $state(false);
  let modalMode = $state<"connect" | "config">("connect");
  let modalProvider = $state<LlmProviderId>("groq");
  let modalKey = $state("");
  let modalBaseUrl = $state("");
  let modalModel = $state("");
  let modalFallback = $state("");
  let modalBusy = $state(false);
  let modalError = $state("");

  const activeId = $derived((settingsForm.LLM_PROVIDER ?? "groq") as LlmProviderId);
  const connectedList = $derived(
    LLM_PROVIDERS.filter((p) => isProviderConnected(p.id, settingsForm)),
  );
  const availableList = $derived(
    LLM_PROVIDERS.filter((p) => !isProviderConnected(p.id, settingsForm)),
  );
  const modalMeta = $derived(providerMeta(modalProvider));
  const modalModels = $derived(modelsForProvider(modalProvider, modalModel));

  async function loadSettings() {
    if (!connection.connected) {
      const ok = await connection.connect({ restart: true });
      if (!ok) return;
    }
    try {
      settings = await api.getSettings();
      settingsForm = { ...settings.values };
      if (!settingsForm.LLM_PROVIDER) settingsForm.LLM_PROVIDER = "groq";
      if (!settingsForm.LLM_MODEL) settingsForm.LLM_MODEL = GROQ_DEFAULT_MODEL;
      if (!settingsForm.EMBEDDING_PROVIDER) settingsForm.EMBEDDING_PROVIDER = "fastembed";
      if (!settingsForm.EMBEDDING_MODEL) {
        settingsForm.EMBEDDING_MODEL =
          settingsForm.EMBEDDING_PROVIDER === "ollama"
            ? "nomic-embed-text"
            : settingsForm.EMBEDDING_PROVIDER === "openai_compatible"
              ? "text-embedding-3-small"
              : "BAAI/bge-small-en-v1.5";
      }
      if (!settingsForm.LLM_FAST_MODEL) settingsForm.LLM_FAST_MODEL = "";
      if (!settingsForm.ENABLE_WEB_SEARCH) settingsForm.ENABLE_WEB_SEARCH = "true";
      if (!settingsForm.ENABLE_ARXIV) settingsForm.ENABLE_ARXIV = "true";
      if (!settingsForm.MAX_GOAL_PASSES) settingsForm.MAX_GOAL_PASSES = "2";
      if (!settingsForm.WATCH_MAX_PASSES) settingsForm.WATCH_MAX_PASSES = "1";
      if (!settingsForm.MIN_GOAL_CONFIDENCE) settingsForm.MIN_GOAL_CONFIDENCE = "0.65";
      if (!settingsForm.AUTO_MEMORY) settingsForm.AUTO_MEMORY = "true";
      if (!settingsForm.DAILY_REVIEW_ENABLED) settingsForm.DAILY_REVIEW_ENABLED = "true";
      if (!settingsForm.ENABLE_MCP) settingsForm.ENABLE_MCP = "false";
      if (!settingsForm.GROQ_FALLBACK_MODEL) {
        settingsForm.GROQ_FALLBACK_MODEL = GROQ_FALLBACK_MODEL;
      }
      if (!settingsForm.LLM_FALLBACK_MODEL) {
        settingsForm.LLM_FALLBACK_MODEL =
          settingsForm.GROQ_FALLBACK_MODEL || GROQ_FALLBACK_MODEL;
      }
      if (!settingsForm.LLM_API_KEY && settingsForm.GROQ_API_KEY) {
        settingsForm.LLM_API_KEY = settingsForm.GROQ_API_KEY;
      }
      settingsForm.LLM_MODEL = resolveModelForProvider(
        settingsForm.LLM_PROVIDER,
        settingsForm.LLM_MODEL,
      );
    } catch (e) {
      settings = null;
      settingsMessage = e instanceof Error ? e.message : "Failed to load settings";
      settingsError = true;
    }
  }

  async function persist(partial: Record<string, string>) {
    const next = { ...settingsForm, ...partial };
    if ((next.LLM_PROVIDER ?? "groq") === "groq" && next.GROQ_API_KEY) {
      next.LLM_API_KEY = next.GROQ_API_KEY;
    }
    if (next.LLM_FALLBACK_MODEL) {
      next.GROQ_FALLBACK_MODEL = next.LLM_FALLBACK_MODEL;
    }
    settingsForm = next;
    await api.updateSettings(next);
    await assistant.loadHarnessDefaults();
    await loadSettings();
    await connection.refreshStatus();
    const llmKeys = new Set([
      "LLM_PROVIDER",
      "LLM_API_KEY",
      "LLM_MODEL",
      "GROQ_API_KEY",
      "OPENAI_API_KEY",
      "OPENROUTER_API_KEY",
      "XAI_API_KEY",
      "CUSTOM_API_KEY",
    ]);
    if ([...Object.keys(partial)].some((k) => llmKeys.has(k)) && connection.cloudWatchConfigured) {
      try {
        await api.cloudWatchSyncLlm();
        await connection.refreshStatus();
      } catch {
        /* Models saved; CW sync optional */
      }
    }
  }

  async function persistPartial(partial: Record<string, string>) {
    settingsSaving = true;
    settingsMessage = "";
    settingsError = false;
    try {
      await persist(partial);
      settingsMessage = connection.reindexRequired
        ? "Saved — rebuilding search index…"
        : "Saved";
      if (connection.reindexRequired) void connection.retryReindex();
    } catch (e) {
      settingsMessage = e instanceof Error ? e.message : "Couldn't save";
      settingsError = true;
    } finally {
      settingsSaving = false;
    }
  }

  function openConnect(id: LlmProviderId) {
    const m = providerMeta(id);
    modalProvider = id;
    modalMode = "connect";
    modalKey = "";
    modalBaseUrl = m.defaultBaseUrl ?? settingsForm.LLM_BASE_URL ?? "";
    modalModel = m.defaultModel ?? "";
    modalFallback = m.defaultFallback ?? "";
    modalError = "";
    modalOpen = true;
  }

  function openConfig(id: LlmProviderId) {
    const m = providerMeta(id);
    modalProvider = id;
    modalMode = "config";
    modalKey = "";
    modalBaseUrl =
      id === activeId
        ? settingsForm.LLM_BASE_URL || m.defaultBaseUrl || ""
        : m.defaultBaseUrl || "";
    modalModel =
      id === activeId
        ? resolveModelForProvider(id, settingsForm.LLM_MODEL)
        : m.defaultModel || "";
    modalFallback =
      id === activeId
        ? settingsForm.LLM_FALLBACK_MODEL || m.defaultFallback || ""
        : m.defaultFallback || "";
    modalError = "";
    modalOpen = true;
  }

  function closeModal() {
    modalOpen = false;
    modalError = "";
  }

  async function submitConnect() {
    const m = providerMeta(modalProvider);
    if (m.needsKey && modalMode === "connect" && !modalKey.trim()) {
      modalError = "API key is required";
      return;
    }
    if (m.needsBaseUrl && !modalBaseUrl.trim()) {
      modalError = "Base URL is required";
      return;
    }
    modalBusy = true;
    modalError = "";
    settingsMessage = "";
    settingsError = false;
    try {
      const patch: Record<string, string> = {
        LLM_PROVIDER: modalProvider,
        LLM_MODEL: resolveModelForProvider(modalProvider, modalModel),
        LLM_FALLBACK_MODEL: modalFallback.trim(),
      };
      if (m.defaultBaseUrl || m.needsBaseUrl || modalBaseUrl.trim()) {
        patch.LLM_BASE_URL = modalBaseUrl.trim() || m.defaultBaseUrl || "";
      }
      if (m.keyEnv) {
        if (modalKey.trim()) {
          patch[m.keyEnv] = modalKey.trim();
          patch.LLM_API_KEY = modalKey.trim();
        } else if (modalMode === "connect") {
          modalError = "API key is required to connect";
          modalBusy = false;
          return;
        }
      }
      if (modalProvider === "openrouter") {
        patch.LLM_BASE_URL =
          modalBaseUrl.trim() || m.defaultBaseUrl || "https://openrouter.ai/api/v1";
      }
      if (modalProvider === "openai_compatible" && modalBaseUrl.trim()) {
        patch.CUSTOM_BASE_URL = modalBaseUrl.trim();
        patch.LLM_BASE_URL = modalBaseUrl.trim();
      }
      if (modalProvider === "xai" && m.defaultBaseUrl) {
        patch.LLM_BASE_URL = modalBaseUrl.trim() || m.defaultBaseUrl;
      }
      await persist(patch);
      closeModal();
      settingsMessage =
        modalMode === "connect" ? `Connected ${m.label}` : `Updated ${m.label}`;
    } catch (e) {
      modalError = e instanceof Error ? e.message : "Couldn't save";
    } finally {
      modalBusy = false;
    }
  }

  async function setActive(id: LlmProviderId) {
    if (!isProviderConnected(id, settingsForm)) return;
    settingsSaving = true;
    settingsMessage = "";
    settingsError = false;
    try {
      const m = providerMeta(id);
      const patch: Record<string, string> = {
        LLM_PROVIDER: id,
        LLM_MODEL: resolveModelForProvider(id, settingsForm.LLM_MODEL),
      };
      if (m.defaultBaseUrl) patch.LLM_BASE_URL = m.defaultBaseUrl;
      if (m.defaultFallback) patch.LLM_FALLBACK_MODEL = m.defaultFallback;
      if (m.keyEnv && settingsForm[m.keyEnv]?.trim()) {
        patch.LLM_API_KEY = settingsForm[m.keyEnv];
      }
      await persist(patch);
      settingsMessage = `Active: ${m.label}`;
    } catch (e) {
      settingsMessage = e instanceof Error ? e.message : "Couldn't switch provider";
      settingsError = true;
    } finally {
      settingsSaving = false;
    }
  }

  async function disconnect(id: LlmProviderId) {
    const m = providerMeta(id);
    if (!m.needsKey) return;
    if (!confirm(`Disconnect ${m.label}? This removes the stored API key.`)) return;
    settingsSaving = true;
    settingsMessage = "";
    settingsError = false;
    try {
      const patch: Record<string, string> = {};
      if (m.keyEnv) patch[m.keyEnv] = "";
      if (id === "openai_compatible") {
        patch.CUSTOM_BASE_URL = "";
      }

      if (activeId === id) {
        let chosen: LlmProviderId = "ollama";
        for (const p of LLM_PROVIDERS) {
          if (p.id === id || p.id === "ollama") continue;
          if (p.keyEnv && settingsForm[p.keyEnv]?.trim()) {
            chosen = p.id;
            break;
          }
        }
        const nm = providerMeta(chosen);
        patch.LLM_PROVIDER = chosen;
        patch.LLM_MODEL = nm.defaultModel ?? "qwen3:8b";
        patch.LLM_FALLBACK_MODEL = nm.defaultFallback ?? "";
        if (nm.keyEnv && settingsForm[nm.keyEnv]?.trim()) {
          patch.LLM_API_KEY = settingsForm[nm.keyEnv];
        } else {
          patch.LLM_API_KEY = "";
        }
        patch.LLM_BASE_URL = nm.defaultBaseUrl ?? "";
      }
      await persist(patch);
      settingsMessage = `Disconnected ${m.label}`;
    } catch (e) {
      settingsMessage = e instanceof Error ? e.message : "Couldn't disconnect";
      settingsError = true;
    } finally {
      settingsSaving = false;
    }
  }

  async function retry() {
    settingsMessage = "";
    settingsError = false;
    settings = null;
    const ok = await connection.connect({ restart: true });
    if (ok) await loadSettings();
  }

  async function reloadService() {
    if (reloading) return;
    reloading = true;
    settingsMessage = "";
    settingsError = false;
    try {
      const ok = await connection.reloadService();
      if (ok) {
        await loadSettings();
        settingsMessage = "AI service reloaded.";
      } else {
        settingsError = true;
        settingsMessage = connection.connectionError || "Could not reload the AI service.";
      }
    } finally {
      reloading = false;
    }
  }

  $effect(() => {
    if (app.sheet === "settings") {
      void loadSettings();
    }
  });
</script>

<div class="settings-root">
  {#if tab === "account" || (connection.connected && settings)}
    <div class="st-layout">
      <nav class="st-nav" aria-label="Settings">
        {#each TABS as t}
          <button
            type="button"
            class="st-nav-btn"
            class:active={tab === t.id}
            onclick={() => {
              tab = t.id;
              app.settingsTab = t.id;
            }}
          >
            {t.label}
          </button>
        {/each}
        {#if connection.connected}
          <div class="st-nav-sep" aria-hidden="true"></div>
          <button
            type="button"
            class="st-nav-btn"
            disabled={reloading}
            onclick={() => void reloadService()}
          >
            {reloading ? "Reloading…" : "Reload AI service"}
          </button>
        {/if}
      </nav>
      <div class="st-main ui-scroll">
        {#if settingsMessage && tab !== "account"}
          <p class="st-msg" class:error={settingsError}>{settingsMessage}</p>
        {/if}
        {#if tab === "appearance"}
          <AppearancePage />
        {:else if tab === "account"}
          <AccountPage />
        {:else}
          <ModelsPage
            {settingsForm}
            {activeId}
            {connectedList}
            {availableList}
            saving={settingsSaving}
            onConnect={openConnect}
            onConfig={openConfig}
            onUse={(id) => void setActive(id)}
            onDisconnect={(id) => void disconnect(id)}
            onPersist={(p) => void persistPartial(p)}
          />
        {/if}
      </div>
    </div>
  {:else if connection.connecting}
    <p class="st-offline">Connecting to AI service…</p>
  {:else if !connection.connected}
    <div class="st-offline">
      <p>
        {connection.connectionError ||
          "Can't reach the AI service. Start the sidecar, then retry."}
      </p>
      <code class="cmd">./scripts/start_sidecar.sh</code>
      <Button variant="secondary" onclick={() => void retry()}>Retry connection</Button>
      <p class="st-hint" style="margin-top: 0.85rem">
        Or open Account to sign in without the sidecar:
        <button
          type="button"
          class="st-nav-btn"
          style="display: inline; margin-left: 0.35rem"
          onclick={() => {
            tab = "account";
            app.settingsTab = "account";
          }}
        >
          Account
        </button>
      </p>
    </div>
  {:else}
    <div class="st-offline">
      <p>Loading settings…</p>
      <Button variant="secondary" onclick={() => void loadSettings()}>Reload</Button>
    </div>
  {/if}
</div>

{#if modalOpen}
  <div class="modal-root" role="presentation">
    <div class="modal-backdrop" role="presentation" onclick={closeModal}></div>
    <div
      class="modal"
      role="dialog"
      aria-label="{modalMode === 'connect' ? 'Connect' : 'Configure'} {modalMeta.label}"
    >
      <header class="modal-head">
        <div class="modal-title-row">
          <span class="mono-badge">{modalMeta.monogram}</span>
          <div>
            <h3 class="modal-title">
              {modalMode === "connect" ? "Connect" : "Configure"}
              {modalMeta.label}
            </h3>
            <p class="modal-sub">{modalMeta.short}</p>
          </div>
        </div>
        <button type="button" class="btn-ghost" onclick={closeModal}>Close</button>
      </header>

      <div class="modal-body">
        {#if modalMeta.needsKey}
          <label class="st-field">
            <span class="st-field-label">
              API key
              {#if modalMode === "config"}
                <span class="st-opt">leave blank to keep</span>
              {/if}
            </span>
            <input
              class="st-control"
              type="password"
              bind:value={modalKey}
              placeholder={modalMeta.keyPlaceholder ?? "API key"}
              autocomplete="off"
            />
          </label>
        {/if}

        {#if modalMeta.needsBaseUrl || modalMeta.showBaseUrl || modalMeta.defaultBaseUrl}
          <label class="st-field">
            <span class="st-field-label">
              Base URL
              {#if !modalMeta.needsBaseUrl}
                <span class="st-opt">optional</span>
              {/if}
            </span>
            <input
              class="st-control"
              bind:value={modalBaseUrl}
              placeholder={modalMeta.defaultBaseUrl ?? "https://…/v1"}
            />
          </label>
        {/if}

        <label class="st-field">
          <span class="st-field-label">Default model</span>
          <input class="st-control" bind:value={modalModel} list="modal-models" />
          <datalist id="modal-models">
            {#each modalModels as model}
              <option value={model}
                >{modelHint(model) ? `${model} — ${modelHint(model)}` : model}</option
              >
            {/each}
          </datalist>
        </label>

        {#if modalMeta.needsKey && modalMeta.defaultFallback}
          <label class="st-field">
            <span class="st-field-label">Fallback model <span class="st-opt">optional</span></span>
            <input class="st-control" bind:value={modalFallback} list="modal-fallback" />
            <datalist id="modal-fallback">
              {#each modalModels as model}
                <option value={model}>{model}</option>
              {/each}
            </datalist>
          </label>
        {/if}

        {#if modalMeta.hint || modalMeta.docsUrl}
          <p class="st-hint">
            {modalMeta.hint ?? ""}
            {#if modalMeta.docsUrl}
              <a href={modalMeta.docsUrl} target="_blank" rel="noreferrer">
                {modalMeta.docsLabel ?? "Docs"}
              </a>
            {/if}
          </p>
        {/if}

        {#if modalError}
          <p class="st-msg error">{modalError}</p>
        {/if}
      </div>

      <footer class="modal-foot">
        <Button variant="ghost" onclick={closeModal}>Cancel</Button>
        <Button variant="primary" disabled={modalBusy} onclick={() => void submitConnect()}>
          {#if modalBusy}
            Saving…
          {:else if modalMode === "connect"}
            Connect
          {:else}
            Save
          {/if}
        </Button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .settings-root {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    min-height: 0;
    height: 100%;
  }

  .cmd {
    display: block;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.5rem 0.65rem;
    margin: 0.5rem 0 0.75rem;
  }

  .mono-badge {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.35rem;
    height: 2.35rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    font-family: var(--font-mono);
    background: color-mix(in srgb, var(--selection-hover) 22%, var(--surface));
    color: var(--accent-link);
  }

  .btn-ghost {
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-normal);
    min-height: 30px;
    padding: 0.25rem 0.55rem;
    border-radius: var(--radius-feedback);
  }

  .btn-ghost:hover:not(:disabled) {
    color: var(--text);
    background: var(--surface-hover);
  }

  .modal-root {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }

  .modal-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
  }

  .modal {
    position: relative;
    width: min(420px, 100%);
    max-height: min(80vh, 640px);
    overflow: auto;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
  }

  .modal-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 1rem 1rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .modal-title-row {
    display: flex;
    gap: 0.65rem;
    align-items: center;
  }

  .modal-title {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .modal-sub {
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .modal-body {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .modal-foot {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    padding: 0.75rem 1rem 1rem;
    border-top: 1px solid var(--border-subtle);
  }
</style>
