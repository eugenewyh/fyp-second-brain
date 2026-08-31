<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import { ensureProjectFolder } from "$lib/vault/load";
  import { ChevronDown, Folder, Pencil, Plus, Search } from "@lucide/svelte";

  interface Topic {
    name: string;
    path: string;
  }

  interface Props {
    value: string;
    label: string;
    disabled?: boolean;
    variant?: "plain" | "chip" | "sidebar" | "field";
    allowUnbound?: boolean;
    allowCreate?: boolean;
    searchPlaceholder?: string;
    menuZIndex?: number;
    onSelect: (path: string) => void;
    onNewWorkspace?: () => void;
    onEditWorkspace?: (path: string) => void;
  }

  let {
    value,
    label,
    disabled = false,
    variant = "plain",
    allowUnbound = false,
    allowCreate = false,
    searchPlaceholder = "Search topics…",
    menuZIndex = 40,
    onSelect,
    onNewWorkspace,
    onEditWorkspace,
  }: Props = $props();

  const RECENTS_KEY = "nous-recent-topics";

  let open = $state(false);
  let query = $state("");
  let recents = $state<string[]>(loadRecents());
  let creating = $state(false);
  let newName = $state("");
  let createError = $state("");
  let creatingBusy = $state(false);
  let triggerEl = $state<HTMLButtonElement | null>(null);
  let searchEl = $state<HTMLInputElement | null>(null);
  let createEl = $state<HTMLInputElement | null>(null);
  let menuEl = $state<HTMLDivElement | null>(null);
  let menuPos = $state({ top: 0, left: 0 });

  const topics = $derived(workspace.projectFolders as Topic[]);
  const unbound = $derived(!value);
  const asWorkspace = $derived(variant === "sidebar" || !!onNewWorkspace);
  const currentName = $derived(
    unbound
      ? (label || "New")
      : (topics.find((t) => t.path === value)?.name ?? label ?? "Topic"),
  );
  const createHint = $derived(query.trim());
  const entityLabel = $derived(asWorkspace ? "workspace" : "topic");
  const entityLabelPlural = $derived(asWorkspace ? "Workspaces" : "Topics");
  const entityLabelCap = $derived(asWorkspace ? "Workspace" : "Topic");

  const filtered = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return topics;
    return topics.filter(
      (t) => t.name.toLowerCase().includes(q) || t.path.toLowerCase().includes(q),
    );
  });

  const recentTopics = $derived.by(() => {
    const known = new Map(topics.map((t) => [t.path, t]));
    const out: Topic[] = [];
    for (const path of recents) {
      const t = known.get(path);
      if (t && !out.some((x) => x.path === t.path)) out.push(t);
    }
    if (value && known.has(value) && !out.some((x) => x.path === value)) {
      out.unshift(known.get(value)!);
    }
    return out.slice(0, 4);
  });

  const showRecents = $derived(!query.trim() && topics.length > 4 && recentTopics.length > 0);

  function loadRecents(): string[] {
    try {
      const raw = localStorage.getItem(RECENTS_KEY);
      const parsed = JSON.parse(raw ?? "[]") as unknown;
      return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
    } catch {
      return [];
    }
  }

  function remember(path: string) {
    recents = [path, ...recents.filter((p) => p !== path)].slice(0, 5);
    try {
      localStorage.setItem(RECENTS_KEY, JSON.stringify(recents));
    } catch {
      /* ignore */
    }
  }

  function placeMenu() {
    const r = triggerEl?.getBoundingClientRect();
    if (!r) return;
    const width = 280;
    const left = Math.min(r.left, Math.max(8, window.innerWidth - width - 8));
    menuPos = { top: r.bottom + 6, left };
  }

  function toggle() {
    if (disabled) return;
    if (open) {
      close();
      return;
    }
    query = "";
    creating = false;
    newName = "";
    createError = "";
    open = true;
    recents = loadRecents();
    placeMenu();
    void workspace.syncProjectsFromDisk();
    queueMicrotask(() => searchEl?.focus());
  }

  function close() {
    open = false;
    query = "";
    creating = false;
    newName = "";
    createError = "";
  }

  function choose(path: string) {
    remember(path);
    close();
    if (path !== value) onSelect(path);
  }

  function chooseUnbound() {
    close();
    if (value) onSelect("");
  }

  function startCreate(seed = "") {
    creating = true;
    createError = "";
    newName = seed.trim();
    queueMicrotask(() => createEl?.focus());
  }

  function startWorkspace() {
    close();
    onNewWorkspace?.();
  }

  function startEdit() {
    const path = value;
    close();
    if (path) onEditWorkspace?.(path);
  }

  async function createTopic() {
    const name = newName.trim() || createHint;
    if (!name || creatingBusy) return;
    creatingBusy = true;
    createError = "";
    try {
      const path = await ensureProjectFolder(name);
      await workspace.syncProjectsFromDisk();
      remember(path);
      close();
      onSelect(path);
    } catch (e) {
      createError = e instanceof Error ? e.message : "Couldn't create that topic.";
    } finally {
      creatingBusy = false;
    }
  }

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      },
    };
  }

  $effect(() => {
    if (!open) return;
    const onPtr = (e: PointerEvent) => {
      const t = e.target as Node | null;
      if (triggerEl?.contains(t) || menuEl?.contains(t)) return;
      close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
      }
    };
    const onReposition = () => placeMenu();
    window.addEventListener("pointerdown", onPtr, true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onReposition);
    window.addEventListener("scroll", onReposition, true);
    return () => {
      window.removeEventListener("pointerdown", onPtr, true);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onReposition);
      window.removeEventListener("scroll", onReposition, true);
    };
  });
</script>

<div class="picker" class:chip={variant === "chip"} class:rail={variant === "sidebar"} class:field={variant === "field"}>
  <button
    type="button"
    class="trigger"
    class:muted={unbound}
    class:open={open}
    bind:this={triggerEl}
    disabled={disabled}
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-label={unbound
      ? `Choose ${entityLabel}`
      : `${entityLabelCap}: ${currentName}`}
    onclick={toggle}
  >
    <span class="trigger-label">{currentName}</span>
    <span class="chevron" class:open aria-hidden="true">
      <ChevronDown size={variant === "chip" ? 12 : 14} strokeWidth={2} />
    </span>
  </button>
</div>

{#if open}
  <div
    class="menu"
    use:portal
    bind:this={menuEl}
    role="listbox"
    aria-label={entityLabelPlural}
    style:top="{menuPos.top}px"
    style:left="{menuPos.left}px"
    style:z-index={menuZIndex}
  >
    <label class="search">
      <Search size={13} strokeWidth={2} />
      <input
        bind:this={searchEl}
        bind:value={query}
        type="search"
        placeholder={searchPlaceholder}
        autocomplete="off"
        spellcheck="false"
      />
    </label>

    <div class="list ui-scroll">
      {#if allowUnbound && !query.trim()}
        <button
          type="button"
          class="item unbound-item"
          class:on={unbound}
          role="option"
          aria-selected={unbound}
          onclick={chooseUnbound}
        >
          <span class="item-copy">
            <span>New</span>
            <span class="hint">Nous picks a folder from your chat</span>
          </span>
        </button>
      {/if}

      {#if showRecents}
        <p class="section">Recents</p>
        {#each recentTopics as t (t.path)}
          <button
            type="button"
            class="item"
            class:on={t.path === value}
            role="option"
            aria-selected={t.path === value}
            onclick={() => choose(t.path)}
          >
            <Folder size={14} strokeWidth={1.75} />
            <span>{t.name}</span>
          </button>
        {/each}
      {/if}

      <p class="section">{query.trim() ? "Matches" : entityLabelPlural}</p>
      {#if filtered.length === 0}
        <p class="empty">{query.trim() ? "No matches." : asWorkspace ? "No workspaces yet." : "No topics yet."}</p>
        {#if allowCreate && query.trim()}
          <button type="button" class="item create-item" onclick={() => startCreate(query)}>
            <Plus size={14} strokeWidth={1.75} />
            <span>Create “{query.trim()}”</span>
          </button>
        {/if}
      {:else}
        {#each filtered as t (t.path)}
          <button
            type="button"
            class="item"
            class:on={t.path === value}
            role="option"
            aria-selected={t.path === value}
            onclick={() => choose(t.path)}
          >
            <Folder size={14} strokeWidth={1.75} />
            <span>{t.name}</span>
          </button>
        {/each}
      {/if}
    </div>

    {#if creating || onNewWorkspace || allowCreate || (onEditWorkspace && value)}
      <div class="foot">
        {#if creating}
          <form class="create-form" onsubmit={(e) => { e.preventDefault(); void createTopic(); }}>
            <input
              bind:this={createEl}
              bind:value={newName}
              type="text"
              placeholder="Topic name"
              maxlength="48"
              autocomplete="off"
              spellcheck="false"
              disabled={creatingBusy}
            />
            <button type="submit" class="create-go" disabled={creatingBusy || !(newName.trim() || createHint)}>
              Create
            </button>
          </form>
          {#if createError}
            <p class="create-err">{createError}</p>
          {/if}
        {:else}
          <div class="foot-start">
            {#if onEditWorkspace && value}
              <button type="button" class="foot-btn" onclick={startEdit}>
                <Pencil size={13} strokeWidth={2} />
                Edit workspace
              </button>
            {/if}
            {#if onNewWorkspace}
              <button type="button" class="foot-btn" onclick={startWorkspace}>
                <Plus size={13} strokeWidth={2} />
                New workspace
              </button>
            {:else if allowCreate}
              <button type="button" class="foot-btn" onclick={() => startCreate(query)}>
                <Plus size={13} strokeWidth={2} />
                New topic
              </button>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .picker {
    display: inline-flex;
    min-width: 0;
  }
  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    max-width: 14rem;
    border: none;
    background: transparent;
    padding: 0.1rem 0.15rem;
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
    cursor: pointer;
    border-radius: var(--radius-feedback);
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }
  .trigger.muted {
    color: var(--text-muted);
    font-weight: var(--font-medium);
  }
  /* Cursor-style composer breadcrumb: plain label + chevron */
  .picker:not(.chip):not(.rail):not(.field) .trigger {
    max-width: min(100%, 18rem);
    gap: 0.15rem;
    padding: 0;
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    letter-spacing: -0.01em;
    color: var(--text);
    border-radius: 0;
  }
  .picker:not(.chip):not(.rail):not(.field) .trigger.muted {
    color: var(--text-muted);
    font-weight: var(--font-medium);
  }
  .chip .trigger {
    max-width: 14rem;
    gap: 0.15rem;
    padding: 0.15rem 0.4rem 0.15rem 0.55rem;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    line-height: 1.2;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-full);
    background: var(--control-fill, transparent);
  }
  .chip .trigger.muted {
    color: var(--text-muted);
    font-weight: var(--font-medium);
  }
  .field {
    display: block;
    width: 100%;
    min-width: 0;
  }
  .field .trigger {
    width: 100%;
    max-width: none;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.55rem 0.7rem;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    line-height: 1.2;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--control-fill);
    transition:
      border-color var(--dur-fast) var(--ease-out),
      background var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out);
  }
  .field .trigger.muted {
    color: var(--text-muted);
  }
  .field .trigger:hover:not(:disabled),
  .field .trigger.open:not(:disabled) {
    border-color: var(--text-faint);
    background: var(--bg-elevated);
    color: var(--text);
  }
  .rail {
    display: block;
    width: 100%;
    min-width: 0;
  }
  .rail .trigger {
    max-width: none;
    width: 100%;
    justify-content: space-between;
    gap: 0.35rem;
    padding: 0.4rem 0.5rem;
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    border-radius: var(--radius-md);
  }
  .rail .trigger.muted {
    color: var(--text-muted);
    font-weight: var(--font-medium);
  }
  .chip .trigger:hover:not(:disabled),
  .chip .trigger[aria-expanded="true"] {
    background: var(--chrome-action-hover);
    border-color: var(--border);
  }
  .picker:not(.chip):not(.rail):not(.field) .trigger:hover,
  .picker:not(.chip):not(.rail):not(.field) .trigger[aria-expanded="true"] {
    background: transparent;
    color: var(--text);
  }
  .picker:not(.chip):not(.rail):not(.field) .trigger :global(svg) {
    width: 14px;
    height: 14px;
    opacity: 0.7;
  }
  .rail .trigger:hover,
  .rail .trigger[aria-expanded="true"] {
    background: var(--chrome-action-hover);
  }
  .trigger:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .chevron {
    display: inline-flex;
    flex-shrink: 0;
    transform: rotate(-90deg);
    transform-origin: center;
    transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .chevron.open {
    transform: rotate(0deg);
  }
  .trigger :global(svg) {
    flex-shrink: 0;
    color: var(--text-faint);
  }
  .trigger-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .menu {
    position: fixed;
    z-index: 40;
    width: 280px;
    display: flex;
    flex-direction: column;
    max-height: min(22rem, calc(100vh - 5rem));
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    box-shadow: none;
    transform-origin: top left;
    animation: picker-menu-in 0.2s cubic-bezier(0.4, 0, 0.2, 1) both;
  }

  @keyframes picker-menu-in {
    from {
      opacity: 0;
      transform: translateY(-6px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .chevron {
      transition: none;
    }

    .menu {
      animation: none;
    }
  }
  .search {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.55rem 0.7rem;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-faint);
  }
  .search input {
    flex: 1;
    min-width: 0;
    border: none;
    background: transparent;
    font: inherit;
    font-size: var(--text-sm);
    color: var(--text);
    outline: none;
  }
  .list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 0.35rem 0.35rem 0.45rem;
  }
  .section {
    margin: 0.35rem 0.45rem 0.2rem;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }
  .item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    border-radius: var(--radius-md);
    padding: 0.4rem 0.5rem;
    font: inherit;
    font-size: var(--text-sm);
    color: var(--text);
    cursor: pointer;
  }
  .item :global(svg) {
    flex-shrink: 0;
    color: var(--text-faint);
  }
  .item:hover,
  .item.on {
    background: var(--chrome-action-hover);
  }
  .item.on {
    font-weight: var(--font-semibold);
  }
  .item span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .item-copy {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.05rem;
    text-align: left;
  }
  .item-copy span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .hint {
    font-size: var(--text-2xs);
    font-weight: var(--font-normal);
    color: var(--text-faint);
    letter-spacing: 0;
    text-transform: none;
  }
  .unbound-item {
    margin-bottom: 0.15rem;
  }
  .create-item {
    color: var(--text-muted);
  }
  .empty {
    margin: 0.35rem 0.5rem 0.5rem;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
  .foot {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    padding: 0.4rem 0.45rem;
    border-top: 1px solid var(--border-subtle);
  }
  .foot-start {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.15rem;
    min-width: 0;
  }
  .foot-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border: none;
    background: transparent;
    padding: 0.28rem 0.4rem;
    border-radius: var(--radius-feedback);
    font: inherit;
    font-size: var(--text-xs);
    color: var(--text-muted);
    cursor: pointer;
  }
  .foot-btn:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }
  .create-form {
    display: flex;
    flex: 1;
    min-width: 0;
    gap: 0.35rem;
  }
  .create-form input {
    flex: 1;
    min-width: 0;
    border: 1px solid var(--border-subtle);
    background: var(--control-fill, transparent);
    border-radius: var(--radius-feedback);
    padding: 0.28rem 0.45rem;
    font: inherit;
    font-size: var(--text-xs);
    color: var(--text);
    outline: none;
  }
  .create-form input:focus {
    border-color: var(--border);
  }
  .create-go {
    flex-shrink: 0;
    border: none;
    background: var(--text);
    color: var(--bg);
    border-radius: var(--radius-feedback);
    padding: 0.28rem 0.55rem;
    font: inherit;
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    cursor: pointer;
  }
  .create-go:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .create-err {
    flex-basis: 100%;
    margin: 0.15rem 0.35rem 0;
    font-size: var(--text-2xs);
    color: var(--error, #c45);
  }
</style>
