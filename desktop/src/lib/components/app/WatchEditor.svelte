<script lang="ts">
  import { untrack } from "svelte";
  import { api, type WatchStatus } from "$lib/api";
  import { app } from "$lib/stores/app.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { markdownBodyToHtml } from "$lib/vault/markdown";
  import { ChevronRight, Play, Square } from "@lucide/svelte";
  import TopicPicker from "./TopicPicker.svelte";

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
  let loading = $state(false);
  let saving = $state(false);
  let savedFlash = $state(false);
  let running = $state(false);
  let live = $state("");
  let error = $state("");
  let steer = $state("");
  let steerOpen = $state(false);
  let abort: AbortController | null = null;
  let loadGen = 0;
  let savedTimer: ReturnType<typeof setTimeout> | null = null;

  const apiWatchId = $derived(watchId || "legacy");
  const isDraft = $derived(!!draft);
  const topics = $derived(workspace.projectFolders);
  const topicPath = $derived.by(() => {
    const paths = new Set(topics.map((t) => t.path));
    if (paths.has(projectPath)) return projectPath;
    if (status?.project_path && paths.has(status.project_path)) return status.project_path;
    const tail = projectPath.split(/[\\/]/).pop();
    return topics.find((t) => t.name === tail)?.path ?? projectPath;
  });
  const topicLabel = $derived(status?.topic ?? projectPath.split(/[\\/]/).pop() ?? "Topic");
  let moving = $state(false);

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
        error = "";
        live = "";
        return;
      }
      void reload();
    });
  });

  async function syncCloud(project: string, id: string) {
    if (!connection.cloudWatchConfigured) return;
    if (!id || id === "legacy" || id === "draft") return;
    try {
      const res = await api.cloudWatchSync(project, id);
      if (res.skipped) return;
      live = live || "Synced to Cloud Scheduled Research.";
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Cloud sync failed";
      live = `Saved locally. Cloud sync: ${msg}`;
    }
  }

  async function save(): Promise<WatchStatus | null> {
    loadGen += 1;
    saving = true;
    savedFlash = false;
    error = "";
    live = "";
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
        live = "Saved as draft — fill Focus and Include before activating.";
      } else {
        live = "Saved.";
      }
      if (savedTimer) clearTimeout(savedTimer);
      savedTimer = setTimeout(() => {
        savedFlash = false;
        if (live === "Saved." || live.startsWith("Saved as draft")) live = "";
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
        error = "Fill Focus and Include before activating.";
      } else {
        await syncCloud(projectPath, apiWatchId);
      }
    } catch (e) {
      enabled = !on;
      error = e instanceof Error ? e.message : "Could not update";
    }
  }

  async function setTopic(nextPath: string) {
    if (!nextPath || nextPath === topicPath || moving) return;
    if (isDraft) {
      workspace.setActiveTopic(nextPath);
      onRelocate?.(nextPath);
      return;
    }
    moving = true;
    error = "";
    try {
      await api.updateWatch(projectPath, {
        watchId: apiWatchId,
        name: name.trim() || "Untitled",
        focus: focusDraft,
        include: includeDraft,
        exclude: excludeDraft,
        trustedSources: trustedDraft,
        enabled,
      });
      const w = await api.moveWatch(projectPath, nextPath, apiWatchId);
      workspace.setActiveTopic(w.project_path);
      onMoved?.(w);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not change topic";
      error =
        /\b(404|405)\b/.test(msg) || /not found/i.test(msg)
          ? "Could not change topic. Reload the AI service in Settings, then try again."
          : msg;
    } finally {
      moving = false;
    }
  }

  async function runNow() {
    if (running) return;
    let path = projectPath;
    let id = apiWatchId;
    if (isDraft) {
      const w = await save();
      if (!w) return;
      path = w.project_path;
      id = w.watch_id || "legacy";
    }
    running = true;
    live = "Starting scheduled research…";
    error = "";
    abort = new AbortController();
    try {
      const result = await api.watchStream(
        path,
        (ev) => {
          const d = "detail" in ev && typeof ev.detail === "string" ? ev.detail : "";
          if (d) live = d;
          if (ev.type === "watch_brief") {
            live = ev.slow_day ? "Slow day — nothing new to rehash." : "Brief written";
          }
          if (ev.type === "result") {
            live = ev.result.slow_day ? "Slow day — nothing new to rehash." : "Brief written";
          }
        },
        abort.signal,
        { sessionId: assistant.activeSessionId, watchId: id, force: true },
      );
      live = result.slow_day ? "Slow day — nothing new to rehash." : "Scheduled research finished.";
      workspace.requestVaultRefresh();
      try {
        const w = await api.getWatch(path, id);
        status = w;
        name = w.name || name;
        focusDraft = w.focus?.trim() || focusDraft;
        includeDraft = w.include?.trim() || includeDraft;
        excludeDraft = w.exclude?.trim() || excludeDraft;
        trustedDraft = w.trusted_sources?.trim() || trustedDraft;
        enabled = w.enabled;
      } catch {
        /* list will refresh via vault nonce */
      }
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") live = "Cancelled";
      else error = e instanceof Error ? e.message : "Scheduled research failed";
    } finally {
      running = false;
      abort = null;
    }
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
    <nav class="crumb">
      <button type="button" class="link" onclick={onBack}>Scheduled Research</button>
      <ChevronRight size={14} strokeWidth={2} />
      <span>{name || "Untitled"}</span>
    </nav>
    <div class="bar-actions">
      {#if error}
        <span class="bar-err" role="status">{error}</span>
      {/if}
      <button type="button" class="ghost" disabled={saving} onclick={() => void save()}>
        {saving ? "Saving…" : savedFlash ? "Saved" : "Save"}
      </button>
      {#if running}
        <button type="button" class="ghost" onclick={() => abort?.abort()}>
          <Square size={13} strokeWidth={2} />
          Stop
        </button>
      {:else}
        <button type="button" class="ghost" disabled={loading && !isDraft} onclick={() => void runNow()}>
          <Play size={13} strokeWidth={2} />
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
      <span class="state">{enabled ? "Active" : "Inactive"}</span>
      <span class="vdiv" aria-hidden="true"></span>
      <TopicPicker
        value={topicPath}
        label={topicLabel}
        disabled={moving || saving}
        onSelect={(path) => void setTopic(path)}
      />
    </div>

    <div class="tabs" role="tablist">
      <button type="button" role="tab" aria-selected={tab === "settings"} class:on={tab === "settings"} onclick={() => (tab = "settings")}>
        Settings
      </button>
      <button type="button" role="tab" aria-selected={tab === "history"} class:on={tab === "history"} onclick={() => (tab = "history")}>
        Run history
      </button>
    </div>

    {#if error}
      <p class="err" role="status">{error}</p>
    {:else if running || live}
      <p class="live" role="status">{live}</p>
    {/if}

    {#if tab === "settings"}
      <section>
        <h2>Triggers</h2>
        <div class="card">
          <div class="card-main">
            <p class="card-title">Weekday mornings</p>
            <p class="hint">
              {#if connection.cloudWatchesDelegated}
                When this schedule is active, Cloud Scheduled Research writes a brief on weekday mornings around
                9am — even if this Mac is asleep. Briefs appear here when you open Nous. Use Run for an extra look
                today (rewrites today’s brief).
              {:else if connection.cloudWatchAvailable}
                When this schedule is active, Nous writes a brief on weekday mornings while the app is open.
                Sign in under Settings → Account to run in the cloud while offline.
                Use Run for an extra look today (rewrites today’s brief).
              {:else}
                When this schedule is active, Nous writes a brief on weekday mornings while the app is open.
                If Nous was closed, catch-up runs after the scheduled hour when you reopen.
                Use Run for an extra look today (rewrites today’s brief).
              {/if}
            </p>
          </div>
        </div>
      </section>

      <section>
        <h2>Agent instructions</h2>
        <div class="card stack">
          <label class="field">
            <span>Focus</span>
            <textarea rows="3" bind:value={focusDraft} placeholder="What should this schedule track?"></textarea>
          </label>
          <label class="field">
            <span>Include</span>
            <textarea rows="3" bind:value={includeDraft} placeholder="What counts as significant?"></textarea>
          </label>
          <label class="field">
            <span>Exclude</span>
            <textarea rows="2" bind:value={excludeDraft} placeholder="Noise to ignore (optional)"></textarea>
          </label>
          <label class="field">
            <span>Trusted sources</span>
            <textarea
              rows="2"
              bind:value={trustedDraft}
              placeholder="Publications, arXiv categories, people, repos (optional)"
            ></textarea>
          </label>
        </div>
        {#if isDraft}
          <p class="hint disclose">Save to keep this schedule, then you can add a note for the next run.</p>
        {:else if steerOpen}
          <form
            class="steer"
            onsubmit={(e) => {
              e.preventDefault();
              void submitSteer();
            }}
          >
            <label class="field">
              <span>Note for the next run</span>
              <textarea rows="2" bind:value={steer} placeholder="Ignore HN hype; also watch Elicit…"></textarea>
            </label>
            <div class="steer-actions">
              <button type="button" class="text" onclick={() => (steerOpen = false)}>Cancel</button>
              <button type="submit" class="ghost" disabled={!steer.trim()}>Append</button>
            </div>
          </form>
        {:else}
          <button type="button" class="text disclose" onclick={() => (steerOpen = true)}>
            Add a note for next run
          </button>
        {/if}
      </section>

      <section>
        <h2>Tools</h2>
        <div class="card">
          <div class="card-main">
            <p class="card-title">Memory</p>
            <p class="hint">Looks through this topic’s notes, then the web and arXiv. Writes a brief, not a chat reply.</p>
          </div>
        </div>
      </section>
    {:else}
      <section>
        <h2>Run history</h2>
        {#if !status?.briefs?.length}
          <p class="hint">No briefs yet. Run to write today’s look.</p>
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
      </section>
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
    padding: 0 1.15rem;
    min-height: var(--titlebar-height);
    position: relative;
    z-index: 5;
    -webkit-app-region: drag;
    app-region: drag;
  }
  .bar :global(button) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }
  .crumb {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    min-width: 0;
  }
  .crumb span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
  }
  .link,
  .text {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent-link);
    cursor: pointer;
    font: inherit;
    font-size: var(--text-sm);
  }
  .bar-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .bar-err {
    max-width: 14rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: var(--text-xs);
    color: var(--error);
  }
  .ghost {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: var(--text-sm);
    border: 1px solid var(--border);
    background: var(--control-fill);
    border-radius: var(--radius-full);
    padding: 0.28rem 0.7rem;
    cursor: pointer;
    color: var(--text);
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }
  .ghost:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 1.15rem 1.5rem 2.25rem;
    max-width: 40rem;
    width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
  }
  .title {
    width: 100%;
    border: none;
    background: transparent;
    font: inherit;
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    letter-spacing: -0.03em;
    color: var(--text);
    padding: 0;
    margin: 0 0 0.65rem;
    outline: none;
  }
  .meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1.1rem;
    min-height: 28px;
  }
  .state {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    white-space: nowrap;
    line-height: 1;
  }
  .vdiv {
    width: 1px;
    height: 12px;
    background: var(--border);
    flex-shrink: 0;
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
  .tabs {
    display: flex;
    gap: 0.2rem;
    margin-bottom: 1.35rem;
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
  section {
    margin-bottom: 1.65rem;
  }
  section:last-child {
    margin-bottom: 0;
  }
  h2 {
    margin: 0 0 0.55rem;
    font-size: var(--text-xs);
    font-weight: 620;
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }
  .card {
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    padding: 0.85rem 0.95rem;
    background: var(--control-fill);
  }
  .card.stack {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }
  .card-main {
    min-width: 0;
    flex: 1;
  }
  .card-title {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text);
  }
  .hint {
    margin: 0.28rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.45;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
  textarea {
    display: block;
    width: 100%;
    box-sizing: border-box;
    resize: none;
    font: inherit;
    font-size: var(--text-sm);
    line-height: 1.5;
    padding: 0.5rem 0.6rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    background: var(--bg-elevated);
    color: var(--text);
    min-height: 4.5rem;
  }
  .disclose {
    margin-top: 0.55rem;
  }
  .steer {
    margin-top: 0.7rem;
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
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 0.5rem 0.7rem;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .day {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
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
  .live {
    font-size: var(--text-sm);
    color: var(--text-muted);
    margin: 0 0 0.75rem;
  }
  .err {
    color: var(--error);
    font-size: var(--text-sm);
    margin: 0 0 0.75rem;
  }
</style>
