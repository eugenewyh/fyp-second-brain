<script lang="ts">
  import { tabs } from "$lib/stores/tabs.svelte";
  import type { Component } from "svelte";
  import {
    FlaskConical,
    MessageSquare,
    FileText,
    FolderOpen,
    Settings,
    X,
  } from "@lucide/svelte";

  const icons: Record<string, Component> = {
    research: FlaskConical,
    query: MessageSquare,
    note: FileText,
    ingest: FolderOpen,
    settings: Settings,
  };
</script>

<div class="tab-bar">
  {#each tabs.tabs as tab (tab.id)}
    {@const Icon = icons[tab.type] ?? FileText}
    <button
      class="tab"
      class:active={tabs.activeTabId === tab.id}
      onclick={() => tabs.activate(tab.id)}
    >
      <Icon size={13} strokeWidth={1.75} />
      <span class="tab-label">{tab.label}</span>
      {#if tabs.tabs.length > 1}
        <span
          class="tab-close"
          role="button"
          tabindex="0"
          onclick={(e) => {
            e.stopPropagation();
            tabs.closeTab(tab.id);
          }}
          onkeydown={(e) => {
            if (e.key === "Enter") {
              e.stopPropagation();
              tabs.closeTab(tab.id);
            }
          }}
        >
          <X size={12} strokeWidth={2} />
        </span>
      {/if}
    </button>
  {/each}
</div>

<style>
  .tab-bar {
    display: flex;
    gap: 0;
    padding: 0 0.5rem;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-subtle);
    overflow-x: auto;
    flex-shrink: 0;
    min-height: 34px;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.65rem;
    background: transparent;
    color: var(--text-faint);
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 0.75rem;
    white-space: nowrap;
    border-radius: 0;
    margin-bottom: -1px;
  }

  .tab:hover {
    color: var(--text-muted);
    background: transparent;
  }

  .tab.active {
    color: var(--text);
    border-bottom-color: var(--accent);
  }

  .tab-close {
    display: flex;
    opacity: 0;
    padding: 0.1rem;
    border-radius: 3px;
    color: var(--text-faint);
  }

  .tab:hover .tab-close,
  .tab.active .tab-close {
    opacity: 1;
  }

  .tab-close:hover {
    color: var(--text);
    background: var(--surface-hover);
  }
</style>