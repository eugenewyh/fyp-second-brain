<script lang="ts">
  import { getCommands } from "$lib/workspace/commands";
  import { workspace } from "$lib/stores/workspace.svelte";

  let filter = $state("");
  const commands = getCommands();

  let filtered = $derived(
    filter.trim()
      ? commands.filter((c) => c.label.toLowerCase().includes(filter.toLowerCase()))
      : commands,
  );

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
</script>

{#if workspace.commandPaletteOpen}
  <div
    class="palette-backdrop"
    role="presentation"
    onclick={() => workspace.closeCommandPalette()}
  >
    <div class="palette" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()}>
      <input
        class="palette-input"
        placeholder="Type a command…"
        bind:value={filter}
        onkeydown={onKeydown}
        autofocus
      />
      <ul class="palette-list">
        {#each filtered as cmd (cmd.id)}
          <li>
            <button class="palette-item" onclick={() => runCommand(cmd.id)}>
              <span>{cmd.label}</span>
              {#if cmd.shortcut}
                <span class="shortcut">{cmd.shortcut}</span>
              {/if}
            </button>
          </li>
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
    background: rgba(0, 0, 0, 0.55);
    z-index: 1000;
    display: flex;
    justify-content: center;
    padding-top: 15vh;
  }

  .palette {
    width: min(480px, 90vw);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }

  .palette-input {
    border: none;
    border-bottom: 1px solid var(--border);
    border-radius: 0;
    padding: 0.9rem 1rem;
  }

  .palette-list {
    list-style: none;
    max-height: 320px;
    overflow-y: auto;
    padding: 0.35rem;
  }

  .palette-item {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.75rem;
    background: transparent;
    color: var(--text);
    text-align: left;
    font-size: 0.9rem;
  }

  .palette-item:hover {
    background: var(--surface-hover);
  }

  .shortcut {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .empty {
    padding: 1rem;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
</style>