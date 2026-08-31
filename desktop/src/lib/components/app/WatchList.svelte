<script lang="ts">
  import { api, type WatchListItem } from "$lib/api";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { watchRuns } from "$lib/stores/watchRuns.svelte";
  import { ArrowUpRight, EllipsisVertical, Pencil, Plus, Search, Square, Trash2 } from "@lucide/svelte";

  interface Props {
    onOpen: (item: WatchListItem) => void;
    onNew: () => void;
  }

  let { onOpen, onNew }: Props = $props();

  let watches = $state<WatchListItem[]>([]);
  let loading = $state(false);
  let error = $state("");
  let search = $state("");
  let menu = $state<{ key: string; top: number; left: number } | null>(null);
  let menuEl = $state<HTMLDivElement | null>(null);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let reloading = $state(false);
  let promoting = $state(false);
  let plannerError = $state("");
  let kindFilter = $state<"all" | "scheduled" | "draft" | "legacy">("all");

  const topics = $derived(workspace.projectFolders);
  const topicPath = $derived(
    workspace.activeTopicPath ?? topics[0]?.path ?? null,
  );

  const filtered = $derived.by(() => {
    let rows = watches;
    if (kindFilter === "legacy") rows = rows.filter((w) => !w.watch_id);
    else if (kindFilter === "draft") rows = rows.filter((w) => !!w.watch_id && !w.complete);
    else if (kindFilter === "scheduled") rows = rows.filter((w) => !!w.watch_id && w.complete);
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (w) =>
        w.name.toLowerCase().includes(q) ||
        w.topic.toLowerCase().includes(q),
    );
  });

  async function reload(opts?: { quiet?: boolean }) {
    if (!opts?.quiet) loading = true;
    error = "";
    try {
      const [res, plan] = await Promise.all([
        api.listAllWatches(topics.map((t) => t.path)),
        api.reviewPlan().catch(() => null),
      ]);
      watches = res.watches;
      connection.setBriefsToday(res.watches.filter((w) => w.has_brief_today).length);
      plannerError = plan?.watch_error?.trim() || "";
      connection.watchPlanError = plannerError;
    } catch (e) {
      if (!opts?.quiet) error = e instanceof Error ? e.message : "Could not load schedules";
    } finally {
      if (!opts?.quiet) loading = false;
    }
  }

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void topics.length;
    void reload();
  });

  $effect(() => {
    if (!watchRuns.hasActive) return;
    const id = window.setInterval(() => void reload({ quiet: true }), 4000);
    return () => window.clearInterval(id);
  });

  async function reloadService() {
    if (reloading) return;
    reloading = true;
    error = "";
    try {
      const ok = await connection.reloadService();
      if (!ok) {
        error = connection.connectionError || "Could not reload the AI service.";
        return;
      }
      await reload();
    } finally {
      reloading = false;
    }
  }

  function runFor(w: WatchListItem) {
    return watchRuns.get(w.project_path, w.watch_id || "legacy");
  }

  function rowStatus(w: WatchListItem): {
    label: string;
    detail?: string;
    kind: "running" | "legacy" | "draft" | "paused" | "scheduled" | "brief" | "done" | "error";
  } {
    const run = runFor(w);
    if (run?.phase === "running") {
      return { label: "Running", detail: run.status, kind: "running" };
    }
    if (run?.phase === "done") {
      return { label: "Brief written", detail: run.status, kind: "done" };
    }
    if (run?.phase === "error") {
      return { label: "Failed", detail: run.status, kind: "error" };
    }
    if (run?.phase === "cancelled") {
      return { label: "Cancelled", kind: "error" };
    }
    if (w.has_brief_today) return { label: "Brief ready", kind: "brief" };
    if (!w.watch_id) return { label: "Legacy", kind: "legacy" };
    if (!w.complete) return { label: "Draft", kind: "draft" };
    if (!w.enabled) return { label: "Paused", kind: "paused" };
    return { label: "Scheduled", kind: "scheduled" };
  }

  function relativeTime(iso: string): string {
    if (!iso) return "—";
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return "—";
    const sec = Math.round((Date.now() - t) / 1000);
    if (sec < 45) return "now";
    if (sec < 3600) return `${Math.max(1, Math.round(sec / 60))}m`;
    if (sec < 86400) return `${Math.round(sec / 3600)}h`;
    const days = Math.round(sec / 86400);
    if (days < 14) return `${days}d`;
    return new Date(t).toLocaleDateString();
  }

  function rowKey(w: WatchListItem): string {
    return `${w.project_path}:${w.watch_id}`;
  }

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      },
    };
  }

  function toggleMenu(e: MouseEvent, w: WatchListItem) {
    e.stopPropagation();
    e.preventDefault();
    const key = rowKey(w);
    if (menu?.key === key) {
      menu = null;
      confirmDelete = false;
      return;
    }
    confirmDelete = false;
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const width = 200;
    menu = {
      key,
      top: r.bottom + 4,
      left: Math.min(Math.max(8, r.right - width), window.innerWidth - width - 8),
    };
  }

  function closeMenu() {
    menu = null;
    confirmDelete = false;
  }

  function menuItem(): WatchListItem | undefined {
    if (!menu) return undefined;
    return watches.find((w) => rowKey(w) === menu?.key);
  }

  function editFromMenu() {
    const w = menuItem();
    if (!w) return;
    runAfterMenu(() => onOpen(w));
  }

  async function upgradeFromMenu() {
    const w = menuItem();
    if (!w || w.watch_id || promoting) return;
    promoting = true;
    error = "";
    try {
      const upgraded = await api.promoteWatch(w.project_path, w.name);
      closeMenu();
      workspace.requestVaultRefresh();
      await reload();
      onOpen({
        watch_id: upgraded.watch_id,
        name: upgraded.name,
        project_path: upgraded.project_path,
        topic: upgraded.topic,
        created: upgraded.created,
        enabled: upgraded.enabled,
        complete: upgraded.complete,
        has_brief_today: upgraded.has_brief_today,
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not upgrade";
      error =
        /\b(404|405)\b/.test(msg) || /not found/i.test(msg)
          ? "Could not upgrade. Reload the AI service in Settings, then try again."
          : msg;
    } finally {
      promoting = false;
    }
  }

  async function deleteFromMenu() {
    const w = menuItem();
    if (!w || deleting) return;
    if (!confirmDelete) {
      confirmDelete = true;
      return;
    }
    deleting = true;
    error = "";
    try {
      await api.deleteWatch(w.project_path, w.watch_id || "legacy");
      closeMenu();
      watches = watches.filter((x) => rowKey(x) !== rowKey(w));
      workspace.requestVaultRefresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not delete";
      error =
        /\b(404|405)\b/.test(msg) || /not found/i.test(msg)
          ? "Could not delete. Restart the app so the sidecar loads the latest API."
          : msg;
    } finally {
      deleting = false;
    }
  }

  function runAfterMenu(action: () => void) {
    closeMenu();
    requestAnimationFrame(() => {
      requestAnimationFrame(action);
    });
  }

  $effect(() => {
    if (!menu) return;
    const onPtr = (e: PointerEvent) => {
      const t = e.target as Node | null;
      if (menuEl?.contains(t)) return;
      const el = t instanceof Element ? t.closest(".more") : null;
      if (el) return;
      closeMenu();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMenu();
    };
    const bindId = window.setTimeout(() => {
      window.addEventListener("pointerdown", onPtr, true);
      window.addEventListener("keydown", onKey, true);
    }, 0);
    return () => {
      window.clearTimeout(bindId);
      window.removeEventListener("pointerdown", onPtr, true);
      window.removeEventListener("keydown", onKey, true);
    };
  });
</script>

<div class="watch-list ui-scroll">
  <header class="hero">
    <div>
      <h1>Scheduled Research</h1>
      <p class="sub">
        {#if connection.cloudWatchesDelegated}
          Recurring research briefs for your topics. Active schedules run on weekday mornings in the cloud —
          even when this Mac is asleep. Briefs sync when you open Nous. Or Run anytime.
        {:else if connection.cloudWatchAvailable}
          Recurring research briefs for your topics. Sign in under Settings → Account so weekday mornings run in
          the cloud while you're offline. Without an account, briefs run while Nous is open. Or Run anytime.
        {:else}
          Recurring research briefs for your topics. Active schedules run on weekday mornings while Nous is open;
          if the app was closed, catch-up runs after the scheduled hour when you reopen. Or Run anytime.
        {/if}
      </p>
    </div>
    <div class="hero-actions">
      <button type="button" class="primary" onclick={onNew}>
        <Plus size={15} strokeWidth={2.25} />
        New schedule
      </button>
    </div>
  </header>

  {#if connection.watchesApiStale}
    <p class="err" role="status">
      Scheduled Research routes on this AI service are out of date.
      <button type="button" class="text-btn" disabled={reloading} onclick={() => void reloadService()}>
        {reloading ? "Reloading…" : "Reload AI service"}
      </button>
    </p>
  {/if}

  {#if plannerError}
    <p class="err" role="status" title={plannerError}>
      Morning schedule planning failed: {plannerError}
    </p>
  {/if}

  {#each watchRuns.active as run (run.projectPath + run.watchId)}
    <div class="run-banner" role="status" aria-live="polite">
      <span class="run-dot" aria-hidden="true"></span>
      <div class="run-banner-copy">
        <span class="run-banner-title">{run.name}</span>
        <span class="run-banner-detail">{run.status}</span>
      </div>
      <div class="run-banner-actions">
        <button
          type="button"
          class="banner-btn"
          onclick={() =>
            onOpen({
              watch_id: run.watchId,
              name: run.name,
              project_path: run.projectPath,
              topic: "",
              created: "",
              enabled: true,
              complete: true,
              has_brief_today: false,
            })}
        >
          Open
        </button>
        <button
          type="button"
          class="banner-btn"
          onclick={() => watchRuns.stop(run.projectPath, run.watchId)}
        >
          <Square size={13} strokeWidth={2} />
          Stop
        </button>
      </div>
    </div>
  {/each}

  <div class="toolbar">
    {#if watches.length > 0}
      <div class="filters" role="tablist" aria-label="Filter schedules">
        <button type="button" class:on={kindFilter === "all"} onclick={() => (kindFilter = "all")}>All</button>
        <button type="button" class:on={kindFilter === "scheduled"} onclick={() => (kindFilter = "scheduled")}>Scheduled</button>
        <button type="button" class:on={kindFilter === "draft"} onclick={() => (kindFilter = "draft")}>Drafts</button>
        <button type="button" class:on={kindFilter === "legacy"} onclick={() => (kindFilter = "legacy")}>Legacy</button>
      </div>
    {/if}
    <label class="search">
      <Search size={14} strokeWidth={2} />
      <input type="search" placeholder="Search…" bind:value={search} />
    </label>
  </div>

  {#if error}
    <p class="err" role="status">{error}</p>
  {/if}

  {#if !topicPath}
    <p class="empty">Create a topic first, then add a schedule.</p>
  {:else if loading && watches.length === 0}
    <p class="empty">Loading…</p>
  {:else if filtered.length === 0}
    <p class="empty">
      {search.trim()
        ? "No matches."
        : kindFilter !== "all"
          ? "Nothing in this filter."
          : "No schedules yet — use New schedule to get started."}
    </p>
  {:else}
    <div class="table" role="table">
      <div class="row head" role="row">
        <span>Name</span>
        <span>Topic</span>
        <span>Created</span>
        <span>Status</span>
        <span class="menu-pad" aria-hidden="true"></span>
      </div>
      {#each filtered as w (rowKey(w))}
        {@const st = rowStatus(w)}
        <div class="row item" role="row">
          <button type="button" class="open" onclick={() => onOpen(w)}>
            <span class="name">{w.name || "Untitled"}</span>
            <span class="muted">{w.topic}</span>
            <span class="muted">{relativeTime(w.created)}</span>
            <span class="status {st.kind}" title={st.detail}>
              <span class="status-label">
                {#if st.kind === "running"}
                  <span class="status-dot" aria-hidden="true"></span>
                {/if}
                {st.label}
              </span>
              {#if st.detail && st.kind === "running"}
                <span class="status-detail">{st.detail}</span>
              {/if}
            </span>
          </button>
          <button
            type="button"
            class="more"
            class:on={menu?.key === rowKey(w)}
            aria-label="Schedule actions"
            aria-haspopup="menu"
            aria-expanded={menu?.key === rowKey(w)}
            onclick={(e) => toggleMenu(e, w)}
          >
            <EllipsisVertical size={16} strokeWidth={2} />
          </button>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if menu}
  <div
    class="menu"
    use:portal
    bind:this={menuEl}
    role="menu"
    style:top="{menu.top}px"
    style:left="{menu.left}px"
    onpointerdown={(e) => e.stopPropagation()}
  >
    <button
      type="button"
      class="menu-item"
      role="menuitem"
      onpointerdown={(e) => {
        e.preventDefault();
        e.stopPropagation();
        editFromMenu();
      }}
    >
      <Pencil size={14} strokeWidth={2} />
      Edit details
    </button>
    {#if menuItem() && !menuItem()?.watch_id}
      <button
        type="button"
        class="menu-item"
        role="menuitem"
        disabled={promoting}
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          void upgradeFromMenu();
        }}
      >
        <ArrowUpRight size={14} strokeWidth={2} />
        {promoting ? "Upgrading…" : "Upgrade to named"}
      </button>
    {/if}
    <button
      type="button"
      class="menu-item danger"
      role="menuitem"
      disabled={deleting}
      onpointerdown={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void deleteFromMenu();
      }}
    >
      <Trash2 size={14} strokeWidth={2} />
      {deleting ? "Deleting…" : confirmDelete ? "Confirm delete" : "Delete"}
    </button>
  </div>
{/if}

<style>
  .watch-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 1.25rem 1.5rem 2rem;
    padding-top: calc(var(--titlebar-height) + 0.5rem);
    max-width: 56rem;
    width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
  }
  .hero {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.25rem;
  }
  h1 {
    margin: 0;
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    letter-spacing: -0.03em;
  }
  .sub {
    margin: 0.3rem 0 0;
    color: var(--text-muted);
    font-size: var(--text-sm);
    max-width: 28rem;
  }
  .hero-actions {
    display: flex;
    gap: 0.45rem;
    flex-shrink: 0;
    align-items: center;
  }
  .primary,
  .ghost {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: var(--text-sm);
    border-radius: var(--radius-full);
    padding: 0.35rem 0.85rem;
    cursor: pointer;
    min-height: 32px;
  }
  .primary {
    border: none;
    background: var(--accent-live);
    color: var(--accent-on-live, #ffffff);
    font-weight: var(--font-semibold);
  }
  .primary:disabled {
    opacity: 0.5;
    cursor: wait;
  }
  .ghost {
    border: 1px solid var(--border);
    background: var(--control-fill);
    color: var(--text-muted);
  }
  .ghost.on {
    color: var(--text);
    border-color: var(--text-faint);
  }
  .toolbar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.65rem;
  }
  .filters {
    display: flex;
    gap: 0.15rem;
    margin-right: auto;
  }
  .filters button {
    border: none;
    background: transparent;
    border-radius: var(--radius-full);
    padding: 0.22rem 0.6rem;
    font: inherit;
    font-size: var(--text-xs);
    color: var(--text-faint);
    cursor: pointer;
  }
  .filters button.on {
    background: var(--control-fill);
    color: var(--text);
    font-weight: var(--font-medium);
  }
  .search {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid var(--border);
    background: var(--control-fill);
    border-radius: var(--radius-full);
    padding: 0.2rem 0.65rem;
    color: var(--text-faint);
    min-width: 12rem;
  }
  .search input {
    border: none;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: var(--text-sm);
    width: 100%;
    outline: none;
  }
  .table {
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    overflow: hidden;
  }
  .row {
    display: grid;
    grid-template-columns: 1fr 2.25rem;
    gap: 0;
    width: 100%;
    text-align: left;
    font-size: var(--text-sm);
    align-items: stretch;
  }
  .row.head {
    grid-template-columns: 1.4fr 1fr 0.6fr 1fr 2.25rem;
    gap: 0.5rem;
    padding: 0.55rem 0.85rem;
    color: var(--text-faint);
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-subtle);
    align-items: center;
  }
  .menu-pad {
    width: 2.25rem;
  }
  .row.item {
    background: transparent;
    border-top: 1px solid var(--border-subtle);
    color: var(--text);
  }
  .row.item:first-of-type {
    border-top: none;
  }
  .row.item:hover {
    background: var(--chrome-action-hover);
  }
  .open {
    display: grid;
    grid-template-columns: 1.4fr 1fr 0.6fr 1fr;
    gap: 0.5rem;
    width: 100%;
    min-width: 0;
    text-align: left;
    border: none;
    background: transparent;
    padding: 0.55rem 0.35rem 0.55rem 0.85rem;
    font: inherit;
    color: inherit;
    cursor: pointer;
  }
  .more {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    border: none;
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    border-radius: var(--radius-md);
    margin: 0.2rem 0.3rem 0.2rem 0;
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }
  .more:hover,
  .more.on {
    color: var(--text);
    background: var(--control-fill);
  }
  .name {
    font-weight: var(--font-medium);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .muted {
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .status {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
    align-self: center;
  }

  .status-label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--status-running);
    flex-shrink: 0;
    animation: pulse-live 1.4s ease-in-out infinite;
  }

  .status-detail {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .status.scheduled {
    color: var(--success);
  }
  .status.brief {
    color: var(--accent-live, var(--success));
    font-weight: var(--font-medium);
  }
  .status.running {
    color: var(--accent-live, var(--success));
    font-weight: var(--font-medium);
  }
  .status.done {
    color: var(--success);
  }
  .status.error {
    color: var(--error);
  }
  .run-banner {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 0.85rem;
    padding: 0.65rem 0.8rem;
    border: 1px solid color-mix(in srgb, var(--accent-live) 35%, var(--border));
    border-radius: var(--radius-xl);
    background: color-mix(in srgb, var(--accent-live) 8%, var(--bg-elevated));
  }
  .run-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--status-running);
    flex-shrink: 0;
    animation: pulse-live 1.4s ease-in-out infinite;
  }
  .run-banner-copy {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
    flex: 1;
  }
  .run-banner-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
  }
  .run-banner-detail {
    font-size: var(--text-xs);
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .run-banner-actions {
    display: flex;
    gap: 0.35rem;
    flex-shrink: 0;
  }
  .banner-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    border: 1px solid var(--border);
    background: var(--control-fill);
    border-radius: var(--radius-full);
    padding: 0.22rem 0.6rem;
    font: inherit;
    font-size: var(--text-xs);
    color: var(--text);
    cursor: pointer;
    min-height: 28px;
  }
  .banner-btn:hover {
    background: var(--chrome-action-hover);
  }
  .status.paused,
  .status.draft {
    color: var(--text-faint);
  }
  .status.legacy {
    color: var(--text-muted);
  }
  .text-btn {
    display: inline;
    margin-left: 0.35rem;
    background: none;
    border: none;
    padding: 0;
    color: var(--accent-link);
    cursor: pointer;
    font: inherit;
    font-size: inherit;
  }
  .text-btn:disabled {
    opacity: 0.5;
    cursor: wait;
  }
  .menu {
    position: fixed;
    z-index: 1400;
    width: 200px;
    padding: 0.3rem;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: none;
    -webkit-app-region: no-drag;
    app-region: no-drag;
    pointer-events: auto;
  }
  .menu-item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    border: none;
    background: transparent;
    border-radius: var(--radius-md);
    padding: 0.42rem 0.5rem;
    font: inherit;
    font-size: var(--text-sm);
    color: var(--text);
    cursor: pointer;
    text-align: left;
  }
  .menu-item :global(svg) {
    color: var(--text-faint);
    flex-shrink: 0;
  }
  .menu-item:hover {
    background: var(--chrome-action-hover);
  }
  .menu-item.danger {
    color: var(--error);
  }
  .menu-item.danger :global(svg) {
    color: var(--error);
  }
  .menu-item:disabled {
    opacity: 0.5;
    cursor: wait;
  }
  .empty,
  .err {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
  .err {
    color: var(--error);
  }
</style>
