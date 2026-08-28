<script lang="ts">
  import { onMount } from "svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import {
    createProjectFolder,
    getVaultRoot,
    listProjectFolders,
  } from "$lib/vault/load";
  import { monogram } from "$lib/vault/topics";

  interface Props {
    /** compact = chip under center composer */
    compact?: boolean;
  }

  let { compact = true }: Props = $props();

  let open = $state(false);
  let query = $state("");
  let projects = $state<{ name: string; path: string }[]>([]);
  let loading = $state(false);
  let adding = $state(false);
  let newName = $state("");
  let error = $state("");
  let rootEl: HTMLDivElement | undefined = $state();

  const activePath = $derived(
    assistant.activeSession?.projectPath !== undefined
      ? assistant.activeSession.projectPath
      : workspace.activeTopicPath,
  );

  const SYSTEM = new Set(["research", "memory"]);

  const userProjects = $derived(
    projects.filter((p) => !SYSTEM.has(p.name.toLowerCase())),
  );

  const activeLabel = $derived.by(() => {
    if (!activePath) return "Select project";
    const hit = userProjects.find((p) => p.path === activePath);
    return hit?.name ?? activePath.split(/[\\/]/).pop() ?? "Project";
  });

  const activeMono = $derived(activePath ? monogram(activeLabel) : "P");

  const filtered = $derived(
    userProjects.filter((p) => {
      if (!query.trim()) return true;
      return p.name.toLowerCase().includes(query.trim().toLowerCase());
    }),
  );

  async function refresh() {
    loading = true;
    error = "";
    try {
      workspace.vaultRoot = workspace.vaultRoot ?? (await getVaultRoot());
      projects = await listProjectFolders(workspace.vaultRoot);
      const users = projects.filter((p) => !SYSTEM.has(p.name.toLowerCase()));
      // If nothing selected, pick first user project (prefer Inbox)
      if (!activePath && users.length > 0) {
        const inbox = users.find((p) => p.name.toLowerCase() === "inbox");
        select((inbox ?? users[0]).path);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not load projects";
      projects = [];
    } finally {
      loading = false;
    }
  }

  function select(path: string | null) {
    if (!path) return; // require a real project folder
    assistant.setSessionProject(path);
    workspace.setActiveTopic(path);
    open = false;
    query = "";
    adding = false;
  }

  async function addProject() {
    const name = newName.trim();
    if (!name) return;
    try {
      const path = await createProjectFolder(name);
      workspace.requestVaultRefresh();
      await refresh();
      select(path);
      newName = "";
      adding = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not create project";
    }
  }

  function onDocClick(e: MouseEvent) {
    if (!open || !rootEl) return;
    if (!rootEl.contains(e.target as Node)) {
      open = false;
      adding = false;
    }
  }

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void refresh();
  });

  onMount(() => {
    void refresh();
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  });
</script>

<div class="picker" class:compact bind:this={rootEl}>
  <button
    type="button"
    class="trigger"
    data-testid="project-picker"
    aria-expanded={open}
    aria-haspopup="listbox"
    onclick={() => {
      open = !open;
      if (open) void refresh();
    }}
  >
    <span class="mono" aria-hidden="true">{activeMono}</span>
    <span class="label">{activeLabel}</span>
    <span class="chev" aria-hidden="true">▾</span>
  </button>

  {#if open}
    <div class="menu" role="listbox" aria-label="Projects">
      <div class="search-row">
        <span class="search-ico" aria-hidden="true">⌕</span>
        <input
          class="search"
          type="search"
          placeholder="Search projects"
          bind:value={query}
        />
      </div>

      {#if loading && userProjects.length === 0}
        <p class="hint">Loading…</p>
      {:else if filtered.length === 0 && !adding}
        <p class="hint">{query ? "No matches" : "No projects yet — create one below"}</p>
      {:else}
        {#each filtered as p (p.path)}
          <button
            type="button"
            class="item"
            class:selected={activePath === p.path}
            role="option"
            aria-selected={activePath === p.path}
            onclick={() => select(p.path)}
          >
            <span class="mono">{monogram(p.name)}</span>
            <span class="item-label">{p.name}</span>
            {#if activePath === p.path}
              <span class="check">✓</span>
            {/if}
          </button>
        {/each}
      {/if}

      {#if error}
        <p class="err">{error}</p>
      {/if}

      {#if adding}
        <div class="add-form">
          <input
            class="search"
            placeholder="Project name"
            bind:value={newName}
            onkeydown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void addProject();
              }
              if (e.key === "Escape") {
                adding = false;
                newName = "";
              }
            }}
          />
          <button type="button" class="add-go" onclick={() => void addProject()}>
            Create
          </button>
        </div>
      {:else}
        <button
          type="button"
          class="item add"
          onclick={() => {
            adding = true;
            error = "";
          }}
        >
          <span class="mono faint">+</span>
          <span class="item-label">Add project</span>
        </button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .picker {
    position: relative;
    display: inline-flex;
    flex-direction: column;
    align-items: flex-start;
  }

  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-height: 32px;
    padding: 0.3rem 0.55rem 0.3rem 0.3rem;
    border-radius: var(--radius-lg);
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-normal);
    cursor: pointer;
  }

  .trigger:hover {
    color: var(--text);
    border-color: var(--border-subtle);
    background: rgba(255, 255, 255, 0.03);
  }

  .picker.compact .trigger {
    padding-left: 0.2rem;
  }

  .mono {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.55rem;
    height: 1.55rem;
    border-radius: var(--radius-feedback);
    background: var(--text);
    color: var(--paper);
    font-size: var(--text-xs);
    font-weight: var(--font-semibold);
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .mono.faint {
    background: var(--bg-elevated);
    color: var(--text-faint);
  }

  .label {
    max-width: 12rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chev {
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .menu {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 60;
    min-width: 15rem;
    max-width: 18rem;
    max-height: 16rem;
    overflow-y: auto;
    padding: 0.35rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
  }

  .search-row {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.35rem 0.45rem;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 0.25rem;
  }

  .search-ico {
    color: var(--text-faint);
    font-size: var(--text-base);
  }

  .search {
    flex: 1;
    min-width: 0;
    border: none;
    background: transparent;
    color: var(--text);
    font-size: var(--text-sm);
    padding: 0.25rem 0;
    height: auto;
    width: auto;
  }

  .search:focus {
    outline: none;
    border: none;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    text-align: left;
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-normal);
    min-height: 32px;
    padding: 0.35rem 0.4rem;
    border-radius: var(--radius-feedback);
  }

  .item:hover {
    background: var(--surface-hover);
    color: var(--text);
  }

  .item.selected {
    color: var(--text);
  }

  .item.add {
    margin-top: 0.15rem;
    border-top: 1px solid var(--border-subtle);
    border-radius: 0 0 var(--radius-feedback) var(--radius-feedback);
    color: var(--text-faint);
  }

  .item-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .check {
    color: var(--text);
    font-size: var(--text-sm);
  }

  .hint,
  .err {
    font-size: var(--text-xs);
    color: var(--text-faint);
    padding: 0.4rem 0.45rem;
  }

  .err {
    color: var(--error);
  }

  .add-form {
    display: flex;
    gap: 0.35rem;
    padding: 0.35rem 0.25rem;
    border-top: 1px solid var(--border-subtle);
    margin-top: 0.15rem;
  }

  .add-form .search {
    border: 1px solid var(--border);
    border-radius: var(--radius-feedback);
    padding: 0.3rem 0.45rem;
    background: var(--surface);
  }

  .add-go {
    background: var(--accent-live);
    color: var(--accent-on-live, #ffffff);
    font-size: var(--text-xs);
    min-height: 28px;
    padding: 0.25rem 0.55rem;
    border-radius: var(--radius-feedback);
  }
</style>
