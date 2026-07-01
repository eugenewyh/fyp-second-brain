<script lang="ts">
  import { getCommands, type CommandCategory } from "$lib/workspace/commands";
  import { workspace } from "$lib/stores/workspace.svelte";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";
  import { Search } from "@lucide/svelte";

  let filter = $state("");
  const commands = getCommands();

  const categoryLabels: Record<CommandCategory, string> = {
    navigation: "Navigation",
    research: "Research",
    vault: "Vault",
  };

  let filtered = $derived(
    filter.trim()
      ? commands.filter((c) => c.label.toLowerCase().includes(filter.toLowerCase()))
      : commands,
  );

  let grouped = $derived(() => {
    const groups: { category: CommandCategory; items: typeof filtered }[] = [];
    const order: CommandCategory[] = ["navigation", "research", "vault"];
    for (const cat of order) {
      const items = filtered.filter((c) => c.category === cat);
      if (items.length) groups.push({ category: cat, items });
    }
    return groups;
  });

  async function runCommand(id: string) {
    const cmd = commands.find((c) => c.id === id);
    workspace.closeCommandPalette();
    filter = "";
    await cmd?.run();
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") workspace.closeCommandPalette();
    if (e.key === "Enter" && filtered[0]) runCommand(filtered[0].id);
  }

  function onBackdropKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") workspace.closeCommandPalette();
  }

  let inputEl = $state<HTMLInputElement | undefined>();

  $effect(() => {
    if (workspace.commandPaletteOpen) {
      queueMicrotask(() => inputEl?.focus());
    }
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
      aria-label="Command palette"
      tabindex="-1"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <div class="search-row">
        <Search size={16} strokeWidth={1.75} />
        <input
          class="palette-input"
          placeholder="Type a command…"
          bind:value={filter}
          bind:this={inputEl}
          onkeydown={onKeydown}
        />
      </div>
      <ul class="palette-list">
        {#each grouped() as group}
          <li class="group-label">
            <SectionLabel>{categoryLabels[group.category]}</SectionLabel>
          </li>
          {#each group.items as cmd, i (cmd.id)}
            <li>
              <button
                class="palette-item"
                class:highlight={i === 0 && filter.trim()}
                onclick={() => runCommand(cmd.id)}
              >
                <span>{cmd.label}</span>
                {#if cmd.shortcut}
                  <span class="shortcut">{cmd.shortcut}</span>
                {/if}
              </button>
            </li>
          {/each}
        {/each}
        {#if filtered.length === 0}
          <li class="empty">No matching commands</li>
        {/if}
      </ul>
    </div>
  </div>
{/if}

<style>
  .palette-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    justify-content: center;
    padding-top: 12vh;
  }

  .palette {
    width: min(460px, 92vw);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
    overflow: hidden;
  }

  .search-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 0.85rem;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-faint);
  }

  .palette-input {
    border: none;
    background: transparent;
    padding: 0;
    font-size: 0.875rem;
    outline: none;
  }

  .palette-input:focus {
    outline: none;
  }

  .palette-list {
    list-style: none;
    max-height: 340px;
    overflow-y: auto;
    padding: 0.35rem;
  }

  .group-label {
    padding: 0.5rem 0.65rem 0.25rem;
  }

  .palette-item {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.65rem;
    background: transparent;
    color: var(--text);
    text-align: left;
    font-size: 0.8125rem;
    border-radius: var(--radius-sm);
  }

  .palette-item:hover,
  .palette-item.highlight {
    background: var(--surface-hover);
  }

  .shortcut {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-faint);
  }

  .empty {
    padding: 1rem;
    color: var(--text-faint);
    font-size: 0.8125rem;
    text-align: center;
  }
</style>