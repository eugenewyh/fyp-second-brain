<script lang="ts">
  import { untrack } from "svelte";
  import { api, type WatchStatus } from "$lib/api";
  import { app } from "$lib/stores/app.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { ensureProjectFolder } from "$lib/vault/load";
  import { X } from "@lucide/svelte";
  import TopicPicker from "./TopicPicker.svelte";
  import {
    WATCH_BLUEPRINTS,
    WATCH_CADENCE_OPTIONS,
    WATCH_HOUR_OPTIONS,
    type WatchCadence,
  } from "./watch-blueprints";

  interface Props {
    open: boolean;
    initialTopicPath?: string | null;
    onClose: () => void;
    onCreated: (watch: WatchStatus) => void;
  }

  let { open, initialTopicPath = null, onClose, onCreated }: Props = $props();

  let busy = $state(false);
  let error = $state("");
  let instructions = $state("");
  let topicPath = $state("");
  let cadence = $state<WatchCadence>("weekdays");
  let hour = $state<number>(9);

  const iconSize = 16;
  const iconStroke = 1.75;

  const topics = $derived(workspace.projectFolders);

  const topicLabel = $derived(
    topics.find((t) => t.path === topicPath)?.name ??
      topicPath.split(/[\\/]/).pop()?.replace(/[-_]/g, " ") ??
      "Choose workspace",
  );

  function defaultTopicPath(): string {
    return initialTopicPath ?? workspace.activeTopicPath ?? topics[0]?.path ?? "";
  }

  function topicLabelFor(path: string): string {
    if (!path) return "this workspace";
    const match = topics.find((t) => t.path === path);
    if (match?.name) return match.name;
    return path.split(/[\\/]/).pop()?.replace(/[-_]/g, " ") ?? "this workspace";
  }

  function reset() {
    busy = false;
    error = "";
    instructions = "";
    topicPath = defaultTopicPath();
    cadence = "weekdays";
    hour = 9;
  }

  function close() {
    onClose();
    reset();
  }

  function onBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape" && open) close();
  }

  $effect(() => {
    if (!open) return;
    untrack(() => reset());
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  });

  async function resolveTopic(): Promise<string | null> {
    if (topicPath) return topicPath;
    try {
      const path = await ensureProjectFolder("Scheduled Research");
      topicPath = path;
      workspace.setActiveTopic(path);
      await workspace.syncProjectsFromDisk();
      return path;
    } catch {
      error = "Couldn't create a workspace for this schedule. Start a chat first.";
      return null;
    }
  }

  async function syncCloud(project: string, id: string) {
    if (!connection.cloudWatchConfigured) return;
    if (!id || id === "legacy" || id === "draft") return;
    try {
      await api.cloudWatchSync(project, id);
    } catch {
      // Non-blocking — schedule is saved locally.
    }
  }

  async function finalizeWatch(body: {
    name: string;
    focus: string;
    include?: string | null;
    cadence: WatchCadence;
    hour: number;
  }) {
    const path = await resolveTopic();
    if (!path) return;

    busy = true;
    error = "";
    try {
      let w = await api.createWatch(path, {
        name: body.name,
        focus: body.focus,
        include: body.include ?? null,
        enabled: true,
        cadence: body.cadence,
        hour: body.hour,
      });
      w = await api.updateWatch(path, {
        watchId: w.watch_id || "legacy",
        enabled: true,
        cadence: body.cadence,
        hour: body.hour,
      });
      workspace.requestVaultRefresh();
      await syncCloud(w.project_path, w.watch_id || "legacy");
      onCreated(w);
      close();
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not create schedule";
    } finally {
      busy = false;
    }
  }

  function nameFromInstructions(text: string): string {
    const line = text
      .split("\n")
      .map((l) => l.trim())
      .find(Boolean);
    if (!line) return "Custom brief";
    return line.length > 48 ? `${line.slice(0, 45)}…` : line;
  }

  async function createCustom() {
    const focus = instructions.trim();
    if (!focus) {
      error = "Add instructions for what this schedule should track.";
      return;
    }
    if (!topicPath) {
      error = "Choose a workspace for this schedule.";
      return;
    }
    await finalizeWatch({
      name: nameFromInstructions(focus),
      focus,
      cadence,
      hour,
    });
  }

  async function createFromPreset(bp: (typeof WATCH_BLUEPRINTS)[number]) {
    if (!topicPath) {
      error = "Choose a workspace for this schedule.";
      return;
    }
    const label = topicLabelFor(topicPath);
    await finalizeWatch({
      name: bp.name,
      focus: bp.focus(label),
      include: bp.include(label),
      cadence: "weekdays",
      hour: 9,
    });
  }

  function formatHour(h: number): string {
    const suffix = h >= 12 ? "PM" : "AM";
    const hour12 = h % 12 === 0 ? 12 : h % 12;
    return `${hour12} ${suffix}`;
  }
</script>

{#if open}
  <div class="watch-create-backdrop" role="presentation" onclick={onBackdrop}>
    <div
      class="overlay-panel dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="watch-create-title"
      onclick={(e) => e.stopPropagation()}
    >
      <header class="head">
        <div class="head-main">
          <h2 id="watch-create-title">New schedule</h2>
          <p class="sub">Choose a workspace and describe what to track. Edit focus and sources later in Edit details.</p>
        </div>
        <button type="button" class="icon-btn" aria-label="Close" disabled={busy} onclick={close}>
          <X size={iconSize} strokeWidth={iconStroke} />
        </button>
      </header>

      <div class="body">
        <div class="field workspace-field">
          <span class="field-label">Workspace</span>
          <TopicPicker
            value={topicPath}
            label={topicLabel}
            disabled={busy}
            searchPlaceholder="Search workspaces…"
            menuZIndex={1300}
            onSelect={(path) => (topicPath = path)}
            onNewWorkspace={() => app.openNewProject()}
          />
        </div>

        <label class="field">
          <span class="field-label">Instructions</span>
          <textarea
            rows="4"
            bind:value={instructions}
            disabled={busy}
            placeholder="e.g. Track new papers and product launches related to home espresso gear."
          ></textarea>
        </label>

        <div class="schedule-card">
          <div class="schedule-group">
            <span class="schedule-label" id="watch-cadence-label">Frequency</span>
            <div
              class="segmented"
              class:is-daily={cadence === "daily"}
              role="radiogroup"
              aria-labelledby="watch-cadence-label"
            >
              <span class="segment-thumb" aria-hidden="true"></span>
              {#each WATCH_CADENCE_OPTIONS as opt (opt.value)}
                <button
                  type="button"
                  role="radio"
                  class="segment"
                  class:on={cadence === opt.value}
                  aria-checked={cadence === opt.value}
                  disabled={busy}
                  onclick={() => (cadence = opt.value)}
                >
                  {opt.label}
                </button>
              {/each}
            </div>
          </div>

          <div class="schedule-group">
            <span class="schedule-label" id="watch-hour-label">Time</span>
            <div class="time-row" role="radiogroup" aria-labelledby="watch-hour-label">
              {#each WATCH_HOUR_OPTIONS as h (h)}
                <button
                  type="button"
                  role="radio"
                  class="time-pill"
                  class:on={hour === h}
                  aria-checked={hour === h}
                  disabled={busy}
                  onclick={() => (hour = h)}
                >
                  {formatHour(h)}
                </button>
              {/each}
            </div>
          </div>
        </div>

        <div class="presets">
          <span class="schedule-label">Start from a preset</span>
          <div class="preset-chips">
            {#each WATCH_BLUEPRINTS as bp (bp.id)}
              {@const Icon = bp.icon}
              <button
                type="button"
                class="preset-chip"
                disabled={busy || !topicPath}
                onclick={() => void createFromPreset(bp)}
              >
                <Icon size={14} strokeWidth={iconStroke} />
                <span>{bp.title}</span>
              </button>
            {/each}
          </div>
          <p class="preset-hint">Presets run weekday mornings at 9 AM. Edit details after creating.</p>
        </div>

        {#if error}
          <p class="err" role="status">{error}</p>
        {/if}

        <div class="actions">
          <button type="button" class="ghost" disabled={busy} onclick={close}>Cancel</button>
          <button
            type="button"
            class="primary"
            disabled={busy || !instructions.trim() || !topicPath}
            onclick={() => void createCustom()}
          >
            {busy ? "Creating…" : "Create schedule"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .watch-create-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1250;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    background: var(--overlay-backdrop);
    animation: overlay-backdrop-in var(--dur-fast) var(--ease-out) both;
    -webkit-app-region: no-drag;
    app-region: no-drag;
    pointer-events: auto;
  }

  .dialog {
    width: min(440px, 94vw);
    max-height: min(600px, 88vh);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 1rem 1rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .head-main {
    min-width: 0;
  }

  .head h2 {
    margin: 0;
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
  }

  .sub {
    margin: 0.25rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.45;
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    min-width: 32px;
    min-height: 32px;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    border-radius: var(--radius-md);
    flex-shrink: 0;
  }

  .icon-btn:hover:not(:disabled) {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .icon-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .body {
    padding: 0.85rem 1rem 1rem;
    overflow-y: auto;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
  }

  .workspace-field :global(.picker) {
    display: block;
    width: 100%;
  }

  .workspace-field :global(.trigger) {
    max-width: 100%;
    padding: 0;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    letter-spacing: normal;
    color: var(--text);
  }

  .workspace-field :global(.trigger.muted) {
    color: var(--text-muted);
  }

  .workspace-field :global(.trigger:hover),
  .workspace-field :global(.trigger.open) {
    background: transparent;
  }

  .field-label {
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .field textarea {
    font: inherit;
    font-size: var(--text-sm);
    color: var(--text);
    border: 1px solid var(--border-subtle);
    background: var(--control-fill);
    border-radius: var(--radius-lg);
    padding: 0.6rem 0.7rem;
    outline: none;
    resize: vertical;
    min-height: 5rem;
    line-height: 1.5;
    transition:
      border-color var(--dur-fast) var(--ease-out),
      background var(--dur-fast) var(--ease-out);
  }

  .field textarea:focus {
    border-color: var(--text-faint);
    background: var(--bg-elevated);
  }

  .schedule-card {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--control-fill);
    padding: 0.75rem;
    margin-bottom: 0.85rem;
  }

  .schedule-group {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .schedule-label {
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .segmented {
    position: relative;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.15rem;
    padding: 0.15rem;
    min-height: 32px;
    box-sizing: border-box;
    border-radius: var(--radius-full);
    background: var(--control-fill);
    border: 1px solid var(--border-subtle);
    --segment-gap: 0.15rem;
    --segment-pad: 0.15rem;
  }

  .segment-thumb {
    position: absolute;
    top: var(--segment-pad);
    left: var(--segment-pad);
    width: calc((100% - (var(--segment-pad) * 2) - var(--segment-gap)) / 2);
    height: calc(100% - (var(--segment-pad) * 2));
    border-radius: var(--radius-full);
    background: var(--bg-elevated, var(--paper));
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    transform: translateX(0);
    transition:
      transform 0.25s cubic-bezier(0.4, 0, 0.2, 1),
      border-color var(--dur-fast) var(--ease-out);
    pointer-events: none;
    z-index: 0;
    will-change: transform;
  }

  .segmented.is-daily .segment-thumb {
    transform: translateX(calc(100% + var(--segment-gap)));
  }

  .segment {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 32px;
    border: none;
    background: transparent;
    border-radius: var(--radius-full);
    padding: 0.3rem 0.75rem;
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    line-height: 1;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .segment:hover:not(:disabled):not(.on) {
    color: var(--text);
  }

  .segment.on {
    color: var(--text);
  }

  .segment:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (prefers-reduced-motion: reduce) {
    .segment-thumb {
      transition: none;
    }

    .segment {
      transition: none;
    }
  }

  .time-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.15rem;
    padding: 0.15rem;
    border-radius: var(--radius-full);
    background: var(--control-fill);
    border: 1px solid var(--border-subtle);
  }

  .time-pill {
    border: 1px solid transparent;
    background: transparent;
    border-radius: var(--radius-full);
    padding: 0.3rem 0.35rem;
    min-height: 32px;
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    line-height: 1;
    color: var(--text-muted);
    cursor: pointer;
    transition:
      border-color var(--dur-fast) var(--ease-out),
      background var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }

  .time-pill:hover:not(:disabled):not(.on) {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .time-pill.on {
    border-color: var(--border);
    background: var(--bg-elevated, var(--paper));
    box-shadow: var(--shadow-sm);
    color: var(--text);
  }

  .time-pill:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .presets {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    margin-bottom: 0.85rem;
  }

  .preset-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .preset-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid var(--border-subtle);
    background: transparent;
    border-radius: var(--radius-full);
    padding: 0.35rem 0.65rem;
    font: inherit;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    cursor: pointer;
    transition:
      border-color var(--dur-fast) var(--ease-out),
      background var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out);
  }

  .preset-chip :global(svg) {
    flex-shrink: 0;
    color: var(--text-faint);
  }

  .preset-chip:hover:not(:disabled) {
    border-color: var(--border);
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .preset-chip:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .preset-hint {
    margin: 0;
    font-size: var(--text-2xs);
    color: var(--text-faint);
    line-height: 1.4;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.45rem;
  }

  .ghost,
  .primary {
    font: inherit;
    font-size: var(--text-sm);
    border-radius: var(--radius-full);
    padding: 0.35rem 0.85rem;
    cursor: pointer;
    min-height: 32px;
  }

  .ghost {
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-muted);
  }

  .primary {
    border: none;
    background: var(--accent-live);
    color: var(--accent-on-live, #ffffff);
    font-weight: var(--font-semibold);
  }

  .ghost:disabled,
  .primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .err {
    margin: 0 0 0.75rem;
    font-size: var(--text-xs);
    color: var(--error);
  }
</style>
