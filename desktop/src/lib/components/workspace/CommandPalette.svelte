<script lang="ts">
  import { getCommands } from "$lib/workspace/commands";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { loadVaultTree, getVaultRoot } from "$lib/vault/load";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import { fuzzySearchHits } from "$lib/vault/search-dispatch";
  import type { VaultNode } from "$lib/vault/types";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";

  type PaletteItem =
    | { kind: "recent"; id: string; label: string; path: string }
    | { kind: "file"; id: string; label: string; path: string }
    | { kind: "command"; id: string; label: string; shortcut?: string; run: () => void | Promise<void> };

  let filter = $state("");
  let selected = $state(0);
  let nodes = $state<VaultNode[]>([]);
  let inputEl = $state<HTMLInputElement | undefined>();

  const commands = getCommands();

  async function ensureTree() {
    if (nodes.length) return;
    try {
      const root = workspace.vaultRoot ?? (await getVaultRoot());
      workspace.vaultRoot = root;
      nodes = await loadVaultTree(root);
    } catch {
      nodes = [];
    }
  }

  $effect(() => {
    if (workspace.commandPaletteOpen) {
      filter = "";
      selected = 0;
      queueMicrotask(() => inputEl?.focus());
      void ensureTree();
    }
  });

  const items = $derived.by((): PaletteItem[] => {
    const q = filter.trim().toLowerCase();
    const out: PaletteItem[] = [];

    // Recent
    for (const path of workspace.recentNotePaths) {
      const name = path.split("/").pop() ?? path;
      if (!q || name.toLowerCase().includes(q) || path.toLowerCase().includes(q)) {
        out.push({ kind: "recent", id: `recent:${path}`, label: name, path });
      }
    }

    // Files (fuzzy)
    if (nodes.length) {
      const hits = q ? fuzzySearchHits(nodes, filter.trim()) : flattenVaultFiles(nodes).slice(0, 12).map((f) => ({
        path: f.path,
        name: f.name,
        score: 0,
      }));
      const recentSet = new Set(workspace.recentNotePaths);
      for (const hit of hits.slice(0, 20)) {
        if (recentSet.has(hit.path)) continue;
        out.push({
          kind: "file",
          id: `file:${hit.path}`,
          label: hit.name,
          path: hit.path,
        });
      }
    }

    // Commands
    const cmds = q
      ? commands.filter((c) => c.label.toLowerCase().includes(q))
      : commands;
    for (const cmd of cmds) {
      out.push({
        kind: "command",
        id: `cmd:${cmd.id}`,
        label: cmd.label,
        shortcut: cmd.shortcut,
        run: cmd.run,
      });
    }

    return out;
  });

  $effect(() => {
    // keep selection in range when filter changes
    void items;
    if (selected >= items.length) selected = Math.max(0, items.length - 1);
  });

  async function runItem(item: PaletteItem) {
    workspace.closeCommandPalette();
    filter = "";
    selected = 0;
    if (item.kind === "command") {
      await item.run();
      return;
    }
    app.openDocument(item.path, {
      label: item.label,
      from: "agent",
    });
    workspace.setActiveNote(item.path);
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      workspace.closeCommandPalette();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (items.length) selected = (selected + 1) % items.length;
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (items.length) selected = (selected - 1 + items.length) % items.length;
      return;
    }
    if (e.key === "Enter" && items[selected]) {
      e.preventDefault();
      void runItem(items[selected]);
    }
  }

  function onBackdropKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") workspace.closeCommandPalette();
  }

  function sectionLabel(kind: PaletteItem["kind"]): string {
    if (kind === "recent") return "Recent";
    if (kind === "file") return "Files";
    return "Actions";
  }

  const grouped = $derived.by(() => {
    const order: PaletteItem["kind"][] = ["recent", "file", "command"];
    const groups: { kind: PaletteItem["kind"]; items: { item: PaletteItem; index: number }[] }[] = [];
    for (const kind of order) {
      const withIndex = items
        .map((item, index) => ({ item, index }))
        .filter(({ item }) => item.kind === kind);
      if (withIndex.length) groups.push({ kind, items: withIndex });
    }
    return groups;
  });
</script>

{#if workspace.commandPaletteOpen}
  <div
    class="palette-backdrop"
    role="presentation"
    onclick={() => workspace.closeCommandPalette()}
    onkeydown={onBackdropKeydown}
  >
    <div
      class="palette"
      role="dialog"
      aria-label="Search library"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="search-row">
        <input
          class="palette-input"
          placeholder="Search library or run a command…"
          bind:value={filter}
          bind:this={inputEl}
          onkeydown={onKeydown}
        />
      </div>
      <ul class="palette-list">
        {#each grouped as group}
          <li class="group-label">
            <SectionLabel>{sectionLabel(group.kind)}</SectionLabel>
          </li>
          {#each group.items as { item, index } (item.id)}
            <li>
              <button
                class="palette-item"
                class:highlight={index === selected}
                onmouseenter={() => (selected = index)}
                onclick={() => runItem(item)}
              >
                <span class="item-main">
                  <span>{item.label}</span>
                </span>
                {#if item.kind === "command" && item.shortcut}
                  <span class="shortcut">{item.shortcut}</span>
                {:else if item.kind !== "command"}
                  <span class="shortcut path">{item.path.split("/").slice(-2).join("/")}</span>
                {/if}
              </button>
            </li>
          {/each}
        {/each}
        {#if items.length === 0}
          <li class="empty">No matching files or commands</li>
        {/if}
      </ul>
    </div>
  </div>
{/if}

<style>
  .palette-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 1000;
    display: flex;
    justify-content: center;
    padding-top: 12vh;
  }

  .palette {
    width: min(480px, 92vw);
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-lg);
    overflow: hidden;
  }

  .search-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-faint);
  }

  .palette-input {
    border: none;
    background: transparent;
    padding: 0;
    font-size: var(--text-base);
    outline: none;
  }

  .palette-input:focus {
    outline: none;
  }

  .palette-list {
    list-style: none;
    max-height: 380px;
    overflow-y: auto;
    padding: 0.4rem;
  }

  .group-label {
    padding: 0.5rem 0.65rem 0.25rem;
  }

  .palette-item {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 0.7rem;
    background: transparent;
    color: var(--text);
    text-align: left;
    font-size: var(--text-sm);
    border-radius: var(--radius);
  }

  .item-main {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }

  .item-main :global(svg) {
    flex-shrink: 0;
    color: var(--text-faint);
  }

  .palette-item:hover,
  .palette-item.highlight {
    background: var(--surface-hover);
  }

  .shortcut {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-faint);
    flex-shrink: 0;
  }

  .shortcut.path {
    font-family: inherit;
    max-width: 40%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty {
    padding: 1rem;
    color: var(--text-faint);
    font-size: var(--text-sm);
    text-align: center;
  }
</style>
