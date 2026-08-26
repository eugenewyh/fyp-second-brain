<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { connection } from "$lib/stores/connection.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { app } from "$lib/stores/app.svelte";
  type CapId =
    | "local-vault"
    | "web-search"
    | "multi-agent"
    | "plan-review"
    | "auto-ingest"
    | "memory"
    | "daily-review";

  type Cap = {
    id: CapId;
    name: string;
    category: string;
    description: string;
    enabled: boolean;
    toggleable?: boolean;
  };

  let selected = $state<CapId>("multi-agent");
  let filterQuery = $state("");
  let loading = $state(true);
  let saving = $state(false);
  let dailyReviewEnabled = $state(true);
  let webSearchEnabled = $state(true);
  let arxivEnabled = $state(true);
  let autoMemory = $state(true);
  let maxGoalPasses = $state("2");
  let watchMaxPasses = $state("1");
  let minConfidence = $state("0.65");
  let tavily = $state(false);
  let llmOk = $state(false);
  let provider = $state("—");
  let model = $state("");

  const caps = $derived.by((): Cap[] => [
    {
      id: "local-vault",
      name: "Local vault retrieval",
      category: "Memory",
      description:
        "Search and cite documents via bundled local embeddings (fastembed by default — Ollama optional). Re-ingest after changing the embedding model.",
      enabled:
        connection.connected &&
        connection.collectionCount > 0 &&
        connection.embeddingsOk &&
        !connection.reindexRequired,
    },
    {
      id: "web-search",
      name: "Web search",
      category: "Research",
      description:
        "Allow Agent goals and Watch to use the web. Off forces local vault-only retrieval.",
      enabled: webSearchEnabled,
      toggleable: true,
    },
    {
      id: "multi-agent",
      name: "Autonomous agent pipeline",
      category: "Agents",
      description:
        "After you set a goal or an Active Watch, Nous runs the research graph inside these limits without asking again. Planner + synthesizer use the main model; Ask/verifier use the optional fast model.",
      enabled: connection.connected && llmOk,
    },
    {
      id: "plan-review",
      name: "Plan review (single-pass)",
      category: "Agents",
      description:
        "Single-pass research may pause for human plan approval before retrieval. Agent goals skip this interrupt.",
      enabled: assistant.planReviewEnabled,
      toggleable: true,
    },
    {
      id: "auto-ingest",
      name: "Vault watcher",
      category: "Ingest",
      description: "Automatically ingest new or changed vault files in the background.",
      enabled: workspace.watcherStatus !== "disabled",
    },
    {
      id: "memory",
      name: "Write memory",
      category: "Memory",
      description:
        "Goals and Watch may write claims, learnings, and project.md after a run. Off still recalls existing notes.",
      enabled: autoMemory && connection.connected,
      toggleable: true,
    },
    {
      id: "daily-review",
      name: "Daily autonomous review",
      category: "Memory",
      description:
        "Scheduled review of new vault notes and Active Watches. Runs only while Nous is open; catch-up fires after the scheduled hour.",
      enabled: dailyReviewEnabled && connection.connected,
      toggleable: true,
    },
  ]);

  const filteredCaps = $derived.by(() => {
    const q = filterQuery.trim().toLowerCase();
    if (!q) return caps;
    return caps.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.category.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q),
    );
  });

  const active = $derived(filteredCaps.find((c) => c.id === selected) ?? filteredCaps[0] ?? caps[0]);

  async function persist(partial: Record<string, string>) {
    saving = true;
    try {
      await api.updateSettings(partial);
      await assistant.loadHarnessDefaults();
    } finally {
      saving = false;
    }
  }

  async function load() {
    loading = true;
    try {
      if (!connection.connected) return;
      const [s, defaults] = await Promise.all([api.getSettings(), api.agentDefaults()]);
      tavily = s.tavily_configured;
      llmOk = s.llm_configured ?? s.groq_configured;
      provider = s.llm_provider || s.values.LLM_PROVIDER || "—";
      model = s.values.LLM_MODEL || "";
      webSearchEnabled = (s.values.ENABLE_WEB_SEARCH ?? "true") !== "false";
      arxivEnabled = (s.values.ENABLE_ARXIV ?? "true") !== "false";
      autoMemory = (s.values.AUTO_MEMORY ?? "true") !== "false";
      dailyReviewEnabled = defaults.daily_review_enabled ?? true;
      maxGoalPasses = s.values.MAX_GOAL_PASSES || String(defaults.max_goal_passes ?? 2);
      watchMaxPasses = s.values.WATCH_MAX_PASSES || String(defaults.watch_max_passes ?? 1);
      minConfidence = s.values.MIN_GOAL_CONFIDENCE || String(defaults.min_goal_confidence ?? 0.65);
      await assistant.loadHarnessDefaults();
    } catch {
      /* ignore */
    } finally {
      loading = false;
    }
  }

  function togglePlanReview() {
    assistant.planReviewEnabled = !assistant.planReviewEnabled;
  }

  function onListToggle(id: CapId, e: MouseEvent) {
    e.stopPropagation();
    if (id === "plan-review") {
      togglePlanReview();
      return;
    }
    if (id === "web-search") {
      const next = !webSearchEnabled;
      webSearchEnabled = next;
      void persist({ ENABLE_WEB_SEARCH: next ? "true" : "false" });
      return;
    }
    if (id === "memory") {
      const next = !autoMemory;
      autoMemory = next;
      void persist({ AUTO_MEMORY: next ? "true" : "false" });
      return;
    }
    if (id === "daily-review") {
      const next = !dailyReviewEnabled;
      dailyReviewEnabled = next;
      void persist({ DAILY_REVIEW_ENABLED: next ? "true" : "false" });
    }
  }

  function onArxivToggle() {
    const next = !arxivEnabled;
    arxivEnabled = next;
    void persist({ ENABLE_ARXIV: next ? "true" : "false" });
  }

  function onBudgetBlur(key: string, value: string) {
    const v = value.trim();
    if (!v) return;
    void persist({ [key]: v });
  }

  onMount(() => {
    void load();
  });

  $effect(() => {
    if (connection.connected) void load();
  });
</script>

<div class="caps" data-testid="capabilities-view">
  <div class="list-col">
    <div class="list-head">
      <input
        class="search"
        type="search"
        placeholder="Filter capabilities…"
        bind:value={filterQuery}
      />
      <span class="hint">Allow-list</span>
    </div>
    <ul class="list">
      {#each filteredCaps as c (c.id)}
        <li>
          <button
            type="button"
            class="item"
            class:active={selected === c.id}
            onclick={() => (selected = c.id)}
          >
            <div class="item-text">
              <span class="name">{c.name}</span>
              <span class="cat">{c.category}</span>
            </div>
            {#if c.toggleable}
              <button
                type="button"
                class="toggle"
                class:on={c.enabled}
                role="switch"
                aria-checked={c.enabled}
                disabled={saving && c.id !== "plan-review"}
                onclick={(e) => onListToggle(c.id, e)}
              >
                <span class="knob"></span>
              </button>
            {:else}
              <span class="status" class:on={c.enabled}>
                {c.enabled ? "On" : "Off"}
              </span>
            {/if}
          </button>
        </li>
      {/each}
    </ul>
  </div>

  <div class="detail">
    {#if loading && !active}
      <p class="muted">Loading…</p>
    {:else if active}
      <div class="detail-head">
        <h1>{active.name}</h1>
        <span class="pill">{active.category}</span>
      </div>
      <p class="desc">{active.description}</p>

      <dl class="meta">
        {#if active.id === "multi-agent" || active.id === "web-search"}
          <div>
            <dt>Provider</dt>
            <dd>{provider}{model ? ` · ${model}` : ""}</dd>
          </div>
          <div>
            <dt>Sidecar</dt>
            <dd>{connection.connected ? "Online" : "Offline"}</dd>
          </div>
        {/if}
        {#if active.id === "local-vault" || active.id === "memory"}
          <div>
            <dt>Memory chunks</dt>
            <dd>{connection.collectionCount.toLocaleString()}</dd>
          </div>
        {/if}
        {#if active.id === "web-search"}
          <div>
            <dt>Tavily</dt>
            <dd>{tavily ? "Configured" : "Not configured"}</dd>
          </div>
          <div>
            <dt>arXiv</dt>
            <dd>{arxivEnabled ? "Allowed" : "Blocked"}</dd>
          </div>
        {/if}
        {#if active.id === "plan-review"}
          <div>
            <dt>Default for single-pass</dt>
            <dd>{assistant.planReviewEnabled ? "Enabled" : "Disabled"}</dd>
          </div>
        {/if}
        {#if active.id === "multi-agent"}
          <div>
            <dt>Goal passes</dt>
            <dd>up to {maxGoalPasses}</dd>
          </div>
          <div>
            <dt>Watch passes</dt>
            <dd>up to {watchMaxPasses}</dd>
          </div>
        {/if}
      </dl>

      {#if active.id === "multi-agent"}
        <div class="budget">
          <label class="budget-field">
            <span>Max goal passes</span>
            <input
              class="budget-input"
              bind:value={maxGoalPasses}
              disabled={saving}
              onblur={() => onBudgetBlur("MAX_GOAL_PASSES", maxGoalPasses)}
            />
          </label>
          <label class="budget-field">
            <span>Max Watch passes</span>
            <input
              class="budget-input"
              bind:value={watchMaxPasses}
              disabled={saving}
              onblur={() => onBudgetBlur("WATCH_MAX_PASSES", watchMaxPasses)}
            />
          </label>
          <label class="budget-field">
            <span>Min confidence</span>
            <input
              class="budget-input"
              bind:value={minConfidence}
              disabled={saving}
              onblur={() => onBudgetBlur("MIN_GOAL_CONFIDENCE", minConfidence)}
            />
          </label>
        </div>
      {/if}

      {#if active.id === "web-search"}
        <div class="row">
          <span>arXiv papers</span>
          <button
            type="button"
            class="toggle"
            class:on={arxivEnabled}
            role="switch"
            aria-checked={arxivEnabled}
            disabled={saving}
            onclick={onArxivToggle}
          >
            <span class="knob"></span>
          </button>
        </div>
      {/if}

      <div class="actions">
        {#if active.id === "web-search" && !tavily}
          <button type="button" class="btn" onclick={() => app.openSheet("settings")}>
            Configure in Settings
          </button>
        {:else if active.id === "local-vault" && connection.collectionCount === 0}
          <button type="button" class="btn" onclick={() => app.openSheet("ingest")}>
            Ingest documents
          </button>
        {:else if active.id === "multi-agent" && !llmOk}
          <button type="button" class="btn" onclick={() => app.openSheet("settings")}>
            Connect AI provider
          </button>
        {:else if active.id === "plan-review"}
          <button type="button" class="btn secondary" onclick={togglePlanReview}>
            {assistant.planReviewEnabled ? "Disable plan review" : "Enable plan review"}
          </button>
        {/if}
      </div>

      <p class="footnote">
        Plan review applies to single-pass research only. Agent goals and Watch run without that
        interrupt, inside the allow-list and budget above.
      </p>
    {/if}
  </div>
</div>

<style>
  .caps {
    display: flex;
    height: 100%;
    min-height: 0;
    background: var(--bg);
  }

  .list-col {
    width: 280px;
    flex-shrink: 0;
    border-right: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .list-head {
    padding: 0.35rem 0.75rem 0.75rem;
    min-height: var(--titlebar-height);
    position: relative;
    z-index: 5;
    -webkit-app-region: drag;
    app-region: drag;
  }
  .list-head :global(input) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .search {
    width: 100%;
    height: 32px;
    padding: 0 0.65rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--text);
    font-size: var(--text-sm);
    margin-bottom: 0.45rem;
  }

  .hint {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
  }

  .list {
    list-style: none;
    margin: 0;
    padding: 0.35rem;
    overflow-y: auto;
    flex: 1;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    border-radius: var(--radius-md);
    padding: 0.55rem 0.6rem;
    cursor: pointer;
    margin-bottom: 0.15rem;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
  }

  .item:hover {
    background: var(--chrome-action-hover);
  }

  .item.active {
    background: var(--accent-live-dim);
  }

  .item-text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .name {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .cat {
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .status {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    font-weight: var(--font-medium);
  }

  .status.on {
    color: var(--success);
  }

  .toggle {
    width: 36px;
    height: 20px;
    min-height: 20px;
    padding: 0;
    border-radius: var(--radius-full);
    border: none;
    background: var(--border);
    position: relative;
    cursor: pointer;
    flex-shrink: 0;
  }

  .toggle:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .toggle.on {
    background: var(--accent-live);
  }

  .knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--control-knob);
    transition: transform 0.12s ease;
  }

  .toggle.on .knob {
    transform: translateX(16px);
  }

  .detail {
    flex: 1;
    min-width: 0;
    padding: 1.5rem 1.75rem;
    overflow-y: auto;
  }

  .detail-head {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-bottom: 0.65rem;
  }

  h1 {
    margin: 0;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
  }

  .pill {
    font-size: var(--text-2xs);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    background: var(--surface-hover);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-full);
    padding: 0.15rem 0.5rem;
  }

  .desc {
    margin: 0 0 1.25rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.55;
    max-width: 36rem;
  }

  .meta {
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    margin: 0 0 1.25rem;
  }

  .meta div {
    display: flex;
    gap: 1rem;
  }

  dt {
    width: 7rem;
    flex-shrink: 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  dd {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text);
  }

  .budget {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 8rem));
    gap: 0.75rem;
    margin-bottom: 1.25rem;
  }

  .budget-field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .budget-input {
    height: 32px;
    padding: 0 0.55rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--text);
    font-size: var(--text-sm);
  }

  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    max-width: 16rem;
    margin-bottom: 1.25rem;
    font-size: var(--text-sm);
    color: var(--text);
  }

  .btn {
    background: var(--accent);
    color: var(--accent-contrast);
    border: none;
    border-radius: var(--radius-md);
    min-height: 34px;
    padding: 0.4rem 0.85rem;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    cursor: pointer;
  }

  .btn.secondary {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
  }

  .footnote {
    margin-top: 1.5rem;
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .muted {
    color: var(--text-muted);
  }
</style>
