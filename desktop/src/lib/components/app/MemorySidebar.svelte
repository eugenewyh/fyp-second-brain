<script lang="ts">
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { memory, GRAPH_TYPE_STYLE, GRAPH_TYPE_COLORS, GRAPH_TYPE_ORDER } from "$lib/stores/memory.svelte";
  import { authSession } from "$lib/auth/auth-session.svelte";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";
  import TopicPicker from "./TopicPicker.svelte";
  import {
    groupPeekConnections,
    parsePeekMeta,
    peekConnectionRows,
    peekKindLabel,
    peekTypeLabel,
  } from "$lib/vault/graph-peek";
  import { vaultNodeTypeLabel } from "$lib/vault/vault-graph";
  import { Plus, Search, Settings, X } from "@lucide/svelte";

  const iconSize = 16;
  const iconStroke = 1.75;

  const selected = $derived(memory.selected);
  const meta = $derived(selected ? parsePeekMeta(memory.selectedBody, selected.label) : null);
  const typeLabel = $derived(selected ? peekTypeLabel(selected.type, selected.id) : "");
  const connectionRows = $derived(peekConnectionRows(groupPeekConnections(memory.neighbors)));
  const searching = $derived(memory.search.trim().length > 0);
  const accountLabel = $derived(authSession.label);
  const accountInitial = $derived(authSession.initial);
  const signedIn = $derived(authSession.signedIn);
</script>

<aside class="memory-sidebar" data-chrome-layer aria-label="Memory">
  <div class="titlebar" data-tauri-drag-region></div>

  <div class="mem-head">
    <span class="brand">Memory</span>
    <button
      type="button"
      class="section-add"
      aria-label="New workspace"
      title="New workspace"
      onclick={() => app.openNewProject()}
    >
      <Plus size={14} strokeWidth={2} />
    </button>
  </div>

  <div class="mem-controls">
    {#if memory.topics.length > 0}
      <TopicPicker
        value={memory.topicFilter ?? ""}
        label="All workspaces"
        variant="sidebar"
        allowAll
        allLabel="All workspaces"
        searchPlaceholder="Search workspaces…"
        onNewWorkspace={() => app.openNewProject()}
        onEditWorkspace={(path) => app.openEditProject(path)}
        onSelect={(path) => {
          memory.topicFilter = path || null;
          if (path) workspace.setActiveTopic(path);
        }}
      />
    {/if}

    <div class="search-box">
      <Search size={14} strokeWidth={2} class="search-icon" />
      <input
        type="search"
        placeholder="Search memory…"
        bind:value={memory.search}
        aria-label="Search memory"
      />
      {#if memory.search}
        <button
          type="button"
          class="clear"
          aria-label="Clear search"
          onclick={() => (memory.search = "")}
        >
          <X size={11} strokeWidth={2.25} />
        </button>
      {/if}
    </div>
    {#if searching}
      <p class="match-count">{memory.matchCount} {memory.matchCount === 1 ? "match" : "matches"}</p>
    {/if}
  </div>

  <div class="mem-scroll ui-scroll">
    <SectionLabel>Types</SectionLabel>
    <div class="types">
      {#each GRAPH_TYPE_ORDER as t (t)}
        <button
          type="button"
          class="type-row"
          class:off={!memory.types[t]}
          onclick={() => memory.toggleType(t)}
          aria-pressed={memory.types[t]}
        >
          <span
            class="shape-swatch"
            class:topic={t === "topic"}
            style:--swatch={GRAPH_TYPE_COLORS[t]}
            style:--swatch-stroke={GRAPH_TYPE_STYLE[t].stroke}
          ></span>
          <span class="type-label">{vaultNodeTypeLabel(t)}</span>
          <span class="count">{memory.counts[t] ?? 0}</span>
        </button>
      {/each}
    </div>

    {#if memory.truncated}
      <p class="hint">
        Showing most-connected {memory.nodeCount} of {memory.totalFiles} files. Filter by workspace
        or search to highlight.
      </p>
    {/if}

    {#if selected && meta}
      <div class="selected">
        <div class="sel-panel">
          <div class="sel-top">
            <div class="sel-titles">
              <span class="sel-type">{typeLabel}</span>
              <span class="sel-title" title={meta.title}>{meta.title}</span>
            </div>
            <button
              type="button"
              class="icon-close"
              title="Clear selection"
              aria-label="Clear selection"
              onclick={() => memory.clearSelection()}
            >
              <X size={16} />
            </button>
          </div>
        </div>
        {#if connectionRows.length > 0}
          <p class="conn-label">Connected · {connectionRows.length}</p>
          <ul class="conn-list">
            {#each connectionRows as row (row.node.id)}
              <li>
                <button type="button" class="conn" onclick={() => memory.selectNode(row.node)}>
                  <span class="conn-name">{row.node.label}</span>
                  <span class="conn-kind">{peekKindLabel(row.kind)}</span>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </div>

  <div class="footer">
    {#if signedIn}
      <button type="button" class="account" onclick={() => app.openSettings("account")} title={accountLabel}>
        <span class="avatar" aria-hidden="true">{accountInitial}</span>
        <span class="account-name">{accountLabel}</span>
      </button>
    {:else}
      <button type="button" class="account" onclick={() => app.openSettings("account")}>
        Sign in
      </button>
    {/if}
    <button
      type="button"
      class="settings-icon"
      class:active={app.sheet === "settings"}
      aria-label="Settings"
      title="Settings"
      onclick={() => app.openSettings("appearance")}
    >
      <Settings size={iconSize} strokeWidth={iconStroke} />
    </button>
  </div>
</aside>

<style>
  .memory-sidebar {
    width: var(--sidebar-width);
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--pane-bg);
    border-right: 1px solid var(--border-subtle);
  }

  .titlebar {
    height: var(--titlebar-height);
    flex-shrink: 0;
    -webkit-app-region: drag;
    app-region: drag;
  }

  .memory-sidebar :global(button),
  .memory-sidebar :global(input),
  .memory-sidebar :global(select) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .mem-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0 0.85rem 0.65rem 1rem;
  }

  .section-add {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    padding: 0;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
  }

  .section-add:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .brand {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
    letter-spacing: -0.01em;
  }

  .footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.35rem 0.5rem 0.55rem;
    border-top: 1px solid var(--border-subtle);
  }

  .account {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    text-align: left;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    min-height: 32px;
    padding: 0.3rem 0.45rem;
    border-radius: var(--radius-feedback);
    cursor: pointer;
  }

  .account:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .avatar {
    flex-shrink: 0;
    width: 1.35rem;
    height: 1.35rem;
    border-radius: var(--radius-full);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    background: var(--control-fill);
    color: var(--text);
  }

  .account-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .settings-icon {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
  }

  .settings-icon:hover,
  .settings-icon.active {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .mem-controls {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0 0.85rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .mem-controls :global(.picker.rail) {
    width: 100%;
  }

  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-box :global(.search-icon) {
    position: absolute;
    left: 8px;
    color: var(--text-faint);
    pointer-events: none;
  }

  .search-box input {
    width: 100%;
    height: 30px;
    padding: 0 28px 0 28px;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
    color: var(--text);
    font-size: var(--text-sm);
  }

  .search-box input:focus {
    outline: none;
    border-color: var(--border-active);
  }

  .search-box input::-webkit-search-cancel-button,
  .search-box input::-webkit-search-decoration,
  .search-box input::-moz-search-cancel-button {
    -webkit-appearance: none;
    appearance: none;
    display: none;
  }

  .clear {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    padding: 0;
    border: none;
    border-radius: 50%;
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
  }

  .clear:hover {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .match-count {
    margin: 0;
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .mem-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 0.75rem 0.85rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .types {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .type-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.4rem;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    cursor: pointer;
    text-align: left;
  }

  .type-row:hover {
    background: var(--chrome-action-hover);
  }

  .type-row.off {
    opacity: 0.45;
  }

  .shape-swatch {
    width: 10px;
    height: 10px;
    flex-shrink: 0;
    border-radius: 50%;
    background: var(--swatch);
    border: 1.5px solid var(--swatch-stroke, transparent);
    box-sizing: border-box;
  }

  .shape-swatch.topic {
    background: color-mix(in srgb, var(--swatch) 18%, transparent);
    border-width: 1.5px;
  }

  .type-label {
    flex: 1;
  }

  .count {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .hint {
    margin: 0.25rem 0 0;
    font-size: var(--text-2xs);
    color: var(--text-faint);
    line-height: 1.4;
  }

  .selected {
    margin-top: 0.75rem;
    padding-top: 0.65rem;
    border-top: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .sel-panel {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: 0.55rem 0.6rem 0.6rem;
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
  }

  .sel-top {
    display: flex;
    align-items: flex-start;
    gap: 0.35rem;
  }

  .sel-titles {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .sel-type {
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .sel-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .icon-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-faint);
    padding: 0.2rem;
    cursor: pointer;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
  }

  .icon-close:hover {
    color: var(--text);
    background: var(--surface-hover);
  }

  .conn-label {
    margin: 0.15rem 0 0;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .conn-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .conn {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.4rem;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    cursor: pointer;
    text-align: left;
  }

  .conn:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .conn-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .conn-kind {
    flex-shrink: 0;
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }
</style>
