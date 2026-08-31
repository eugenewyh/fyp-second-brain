<script lang="ts">
  import { untrack } from "svelte";
  import { api, type WatchStatus } from "$lib/api";
  import { app } from "$lib/stores/app.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { watchRuns } from "$lib/stores/watchRuns.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { markdownBodyToHtml } from "$lib/vault/markdown";
  import { ChevronLeft, ChevronRight, Play, Square } from "@lucide/svelte";

  interface Props {
    projectPath: string;
    watchId: string;
    draft?: { name: string; focus: string; include: string };
    onBack: () => void;
    onMoved?: (watch: WatchStatus) => void;
    onRelocate?: (projectPath: string) => void;
  }

  let { projectPath, watchId, draft, onBack, onMoved, onRelocate }: Props = $props();

  let status = $state<WatchStatus | null>(null);
  let name = $state("Untitled");
  let focusDraft = $state("");
  let includeDraft = $state("");
  let excludeDraft = $state("");
  let trustedDraft = $state("");
  let enabled = $state(false);
  let tab = $state<"settings" | "history">("settings");
  let advancedOpen = $state(false);
  let loading = $state(false);
  let saving = $state(false);
  let savedFlash = $state(false);
  let barNote = $state("");
  let error = $state("");
  let steer = $state("");
  let steerOpen = $state(false);
  let loadGen = 0;
  let savedTimer: ReturnType<typeof setTimeout> | null = null;

  const iconSize = 16;
  const iconStroke = 1.75;

  const apiWatchId = $derived(watchId || "legacy");
  const runEntry = $derived(watchRuns.get(projectPath, apiWatchId));
  const running = $derived(runEntry?.phase === "running");
  const live = $derived(runEntry?.status ?? "");
  const isDraft = $derived(!!draft);
  const topicLabel = $derived(status?.topic ?? projectPath.split(/[\\/]/).pop()?.replace(/[-_]/g, " ") ?? "Workspace");

  const scheduleLine = $derived(
    connection.cloudWatchesDelegated
      ? "Runs weekday mornings in the cloud — briefs sync when you open Nous."
      : connection.cloudWatchAvailable
        ? "Runs weekday mornings while Nous is open. Sign in for cloud runs while offline."
        : "Runs weekday mornings while Nous is open.",
  );

  async function reload() {
    const gen = ++loadGen;
    loading = true;
    error = "";
    try {
      const w = await api.getWatch(projectPath, apiWatchId);
      if (gen !== loadGen) return;
      status = w;
      name = w.name || "Untitled";
      focusDraft = w.focus?.trim() || w.suggested_focus || "";
      includeDraft = w.include?.trim() || "";
      excludeDraft = w.exclude?.trim() || "";
      trustedDraft = w.trusted_sources?.trim() || "";
      enabled = w.enabled;
      advancedOpen = !!(excludeDraft.trim() || trustedDraft.trim());
    } catch (e) {
      if (gen !== loadGen) return;
      error = e instanceof Error ? e.message : "Could not load schedule";
    } finally {
      if (gen === loadGen) loading = false;
    }
  }

  $effect(() => {
    void watchId;
    if (!draft) void projectPath;
    const seed = draft;
    untrack(() => {
      if (seed) {
        loadGen += 1;
        loading = false;
        status = null;
        name = seed.name || "Untitled";
        focusDraft = seed.focus || "";
        includeDraft = seed.include || "";
        excludeDraft = "";
        trustedDraft = "";
        enabled = false;
        advancedOpen = false;
        error = "";
        barNote = "";
        return;
      }
      void reload();
    });
  });

  $effect(() => {
    const phase = runEntry?.phase;
    if (phase === "done") {
      void reload();
    } else if (phase === "error" && runEntry?.status) {
      error = runEntry.status;
    }
  });

  async function syncCloud(project: string, id: string) {
    if (!connection.cloudWatchConfigured) return;
    if (!id || id === "legacy" || id === "draft") return;
    try {
      const res = await api.cloudWatchSync(project, id);
      if (res.skipped) return;
      barNote = barNote || "Synced to Cloud Scheduled Research.";
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Cloud sync failed";
      barNote = `Saved locally. Cloud sync: ${msg}`;
    }
  }

  async function save(): Promise<WatchStatus | null> {
    loadGen += 1;
    saving = true;
    savedFlash = false;
    error = "";
    barNote = "";
    try {
      let w: WatchStatus;
      if (isDraft) {
        w = await api.createWatch(projectPath, {
          name: name.trim() || "Untitled",
          focus: focusDraft.trim() || null,
          include: includeDraft.trim() || null,
          enabled,
        });
        if (excludeDraft.trim() || trustedDraft.trim()) {
          w = await api.updateWatch(w.project_path, {
            watchId: w.watch_id || "legacy",
            exclude: excludeDraft,
            trustedSources: trustedDraft,
            enabled,
          });
        }
        workspace.requestVaultRefresh();
        onMoved?.(w);
      } else {
        w = await api.updateWatch(projectPath, {
          watchId: apiWatchId,
          name: name.trim() || "Untitled",
          focus: focusDraft,
          include: includeDraft,
          exclude: excludeDraft,
          trustedSources: trustedDraft,
          enabled,
        });
      }
      status = w;
      name = w.name?.trim() || name;
      if (w.focus?.trim()) focusDraft = w.focus.trim();
      if (w.include?.trim()) includeDraft = w.include.trim();
      excludeDraft = w.exclude?.trim() || excludeDraft;
      trustedDraft = w.trusted_sources?.trim() || trustedDraft;
      enabled = w.enabled;
      savedFlash = true;
      if (enabled === false && !w.complete) {
        barNote = "Saved — add instructions before activating.";
      } else {
        barNote = "Saved.";
      }
      if (savedTimer) clearTimeout(savedTimer);
      savedTimer = setTimeout(() => {
        savedFlash = false;
        if (barNote === "Saved." || barNote.startsWith("Saved —")) barNote = "";
      }, 1600);
      await syncCloud(w.project_path, w.watch_id || "legacy");
      return w;
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not save";
      return null;
    } finally {
      saving = false;
    }
  }

  async function setEnabled(on: boolean) {
    enabled = on;
    if (isDraft) return;
    try {
      status = await api.updateWatch(projectPath, { watchId: apiWatchId, enabled: on });
      enabled = status.enabled;
      if (on && !status.enabled) {
        error = "Add instructions before activating.";
      } else {
        error = "";
        await syncCloud(projectPath, apiWatchId);
      }
    } catch (e) {
      enabled = !on;
      error = e instanceof Error ? e.message : "Could not update";
    }
  }

  async function runNow() {
    if (running) return;
    let path = projectPath;
    let id = apiWatchId;
    let runName = name.trim() || "Untitled";
    if (isDraft) {
      const w = await save();
      if (!w) return;
      path = w.project_path;
      id = w.watch_id || "legacy";
      runName = w.name?.trim() || runName;
    }
    error = "";
    tab = "history";
    await watchRuns.run({
      projectPath: path,
      watchId: id,
      name: runName,
      sessionId: assistant.activeSessionId,
    });
  }

  async function submitSteer() {
    const note = steer.trim();
    if (!note) return;
    if (isDraft) {
      error = "Save this schedule before adding a note.";
      return;
    }
    try {
      await api.watchSteer(projectPath, note, apiWatchId);
      steer = "";
      steerOpen = false;
      await reload();
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not save note";
    }
  }

  function openBrief(path: string) {
    app.openDocument(path, { from: "agent" });
    workspace.setActiveNote(path);
  }
</script>

<div class="editor">
  <header class="bar" data-tauri-drag-region>
    <button type="button" class="back" aria-label="Back" onclick={onBack}>
      <ChevronLeft size={iconSize} strokeWidth={iconStroke} />
    </button>
    <div class="bar-actions">
      {#if error}
        <span class="bar-err" role="status">{error}</span>
      {:else if running && live}
        <span class="bar-live" role="status">{live}</span>
      {:else if barNote}
        <span class="bar-live" role="status">{barNote}</span>
      {/if}
      <button type="button" class="ghost" disabled={saving} onclick={() => void save()}>
        {saving ? "Saving…" : savedFlash ? "Saved" : "Save"}
      </button>
      {#if running}
        <button
          type="button"
          class="ghost"
          onclick={() => watchRuns.stop(projectPath, apiWatchId)}
        >
          <Square size={iconSize} strokeWidth={iconStroke} />
          Stop
        </button>
      {:else}
        <button type="button" class="ghost" disabled={loading && !isDraft} onclick={() => void runNow()}>
          <Play size={iconSize} strokeWidth={iconStroke} />
          Run
        </button>
      {/if}
    </div>
  </header>

  <div class="body ui-scroll">
    <input class="title" bind:value={name} placeholder="Untitled" aria-label="Schedule name" />

    <div class="meta">
      <button
        type="button"
        class="switch"
        class:on={enabled}
        role="switch"
        aria-checked={enabled}
        aria-label={enabled ? "Active" : "Inactive"}
        onclick={() => void setEnabled(!enabled)}
      >
        <span class="knob"></span>
      </button>
      <span class="state">{enabled ? "Active" : "Paused"}</span>
      <span class="meta-dot" aria-hidden="true">·</span>
      <span class="workspace">{topicLabel}</span>
    </div>

    {#if running}
      <div class="run-card" role="status" aria-live="polite">
        <span class="run-pulse" aria-hidden="true"></span>
        <div class="run-copy">
          <span class="run-title">Researching…</span>
          <span class="run-detail">{live}</span>
        </div>
      </div>
    {/if}

    <div class="tabs" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={tab === "settings"}
        class:on={tab === "settings"}
        onclick={() => (tab = "settings")}
      >
        Details
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={tab === "history"}
        class:on={tab === "history"}
        onclick={() => (tab = "history")}
      >
        Briefs
      </button>
    </div>

    {#if tab === "settings"}
      <p class="schedule-line">{scheduleLine}</p>

      <label class="field">
        <span class="field-label">Instructions</span>
        <textarea
          rows="5"
          bind:value={focusDraft}
          placeholder="What should this schedule track?"
        ></textarea>
      </label>

      <button type="button" class="disclose" onclick={() => (advancedOpen = !advancedOpen)}>
        Advanced
        <span class="chev" class:open={advancedOpen}>
          <ChevronRight size={iconSize} strokeWidth={iconStroke} />
        </span>
      </button>

      {#if advancedOpen}
        <div class="advanced">
          <label class="field">
            <span class="field-label">Include</span>
            <textarea rows="2" bind:value={includeDraft} placeholder="What counts as significant?"></textarea>
          </label>
          <label class="field">
            <span class="field-label">Exclude</span>
            <textarea rows="2" bind:value={excludeDraft} placeholder="Noise to ignore (optional)"></textarea>
          </label>
          <label class="field">
            <span class="field-label">Trusted sources</span>
            <textarea
              rows="2"
              bind:value={trustedDraft}
              placeholder="Publications, arXiv categories, people, repos (optional)"
            ></textarea>
          </label>
        </div>
      {/if}

      {#if isDraft}
        <p class="hint">Save to keep this schedule.</p>
      {:else if steerOpen}
        <form
          class="steer"
          onsubmit={(e) => {
            e.preventDefault();
            void submitSteer();
          }}
        >
          <label class="field">
            <span class="field-label">Note for next run</span>
            <textarea rows="2" bind:value={steer} placeholder="Ignore HN hype; also watch Elicit…"></textarea>
          </label>
          <div class="steer-actions">
            <button type="button" class="text" onclick={() => (steerOpen = false)}>Cancel</button>
            <button type="submit" class="ghost" disabled={!steer.trim()}>Add note</button>
          </div>
        </form>
      {:else}
        <button type="button" class="text" onclick={() => (steerOpen = true)}>
          Add note for next run
        </button>
      {/if}
    {:else}
      {#if !status?.briefs?.length}
        <p class="hint">No briefs yet. Run to write today's look.</p>
      {:else}
        <ul class="history">
          {#each status.briefs as b (b.path)}
            <li>
              <button type="button" class="hist" onclick={() => openBrief(b.path)}>
                <span class="day">{b.day}</span>
                <span class="ex">{b.excerpt}</span>
              </button>
            </li>
          {/each}
        </ul>
      {/if}
      {#if status?.latest_brief}
        <div class="md">{@html markdownBodyToHtml(status.latest_brief)}</div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .editor {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .bar {
    flex-shrink: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.75rem;
    padding: 0 1rem;
    min-height: var(--titlebar-height);
    border-bottom: 1px solid var(--border-subtle);
    position: relative;
    z-index: 5;
    -webkit-app-region: drag;
    app-region: drag;
  }

  .bar :global(button) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .back {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: var(--text-faint);
    border-radius: var(--radius-md);
    cursor: pointer;
    flex-shrink: 0;
  }

  .back:hover {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .bar-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    min-width: 0;
  }

  .bar-err,
  .bar-live {
    max-width: 12rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .bar-err {
    color: var(--error);
  }

  .ghost,
  .text {
    font: inherit;
    cursor: pointer;
  }

  .ghost {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: var(--text-sm);
    border: 1px solid var(--border);
    background: var(--control-fill);
    border-radius: var(--radius-full);
    padding: 0.28rem 0.7rem;
    color: var(--text);
    min-height: 32px;
  }

  .ghost:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .text {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent-link);
    font-size: var(--text-sm);
    margin-top: 0.5rem;
  }

  .body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 1rem 1.25rem 2rem;
    max-width: 36rem;
    width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
  }

  .title {
    width: 100%;
    border: none;
    background: transparent;
    font: inherit;
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
    color: var(--text);
    padding: 0;
    margin: 0 0 0.6rem;
    outline: none;
  }

  .meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-bottom: 1rem;
    min-height: 28px;
  }

  .state,
  .workspace {
    font-size: var(--text-sm);
    line-height: 1;
  }

  .state {
    font-weight: var(--font-medium);
    color: var(--text-muted);
  }

  .workspace {
    color: var(--text-faint);
  }

  .meta-dot {
    color: var(--text-faint);
    line-height: 1;
  }

  .switch {
    width: 36px;
    height: 20px;
    min-width: 36px;
    min-height: 20px;
    padding: 0;
    border: none;
    border-radius: var(--radius-full);
    background: var(--border);
    position: relative;
    cursor: pointer;
    flex-shrink: 0;
  }

  .switch.on {
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
    transition: transform var(--dur-control) var(--ease-out);
  }

  .switch.on .knob {
    transform: translateX(16px);
  }

  .run-card {
    display: flex;
    align-items: flex-start;
    gap: 0.55rem;
    margin-bottom: 1rem;
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);
  }

  .run-pulse {
    width: 8px;
    height: 8px;
    margin-top: 0.35rem;
    border-radius: 50%;
    background: var(--status-running);
    flex-shrink: 0;
    animation: pulse-live 1.4s ease-in-out infinite;
  }

  .run-copy {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }

  .run-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .run-detail {
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.4;
  }

  .tabs {
    display: flex;
    gap: 0.15rem;
    margin-bottom: 1rem;
  }

  .tabs button {
    border: none;
    background: transparent;
    border-radius: var(--radius-full);
    padding: 0.3rem 0.75rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
  }

  .tabs button.on {
    background: var(--control-fill);
    color: var(--text);
    font-weight: var(--font-medium);
  }

  .schedule-line {
    margin: 0 0 0.85rem;
    font-size: var(--text-xs);
    color: var(--text-faint);
    line-height: 1.45;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin: 0 0 0.75rem;
  }

  .field-label {
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  textarea {
    display: block;
    width: 100%;
    box-sizing: border-box;
    resize: vertical;
    font: inherit;
    font-size: var(--text-sm);
    line-height: 1.5;
    padding: 0.6rem 0.7rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-subtle);
    background: var(--control-fill);
    color: var(--text);
    outline: none;
  }

  textarea:focus {
    border-color: var(--text-faint);
    background: var(--bg-elevated);
  }

  .disclose {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    border: none;
    background: transparent;
    padding: 0;
    font: inherit;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    margin-bottom: 0.5rem;
  }

  .disclose :global(svg) {
    display: block;
  }

  .chev {
    display: inline-flex;
    transition: transform var(--dur-fast) var(--ease-out);
  }

  .chev.open {
    transform: rotate(90deg);
  }

  .advanced {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin-bottom: 0.5rem;
    padding: 0.75rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--control-fill);
  }

  .hint {
    margin: 0.5rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .steer {
    margin-top: 0.5rem;
  }

  .steer-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 0.45rem;
  }

  .history {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .hist {
    width: 100%;
    text-align: left;
    background: var(--control-fill);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 0.55rem 0.7rem;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .hist:hover {
    border-color: var(--border);
    background: var(--chrome-action-hover);
  }

  .day {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .ex {
    font-size: var(--text-xs);
    color: var(--text-muted);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .md {
    margin-top: 0.85rem;
    font-size: var(--text-sm);
    line-height: 1.5;
  }
</style>
