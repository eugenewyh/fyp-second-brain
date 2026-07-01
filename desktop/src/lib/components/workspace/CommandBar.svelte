<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import StatusDot from "$lib/ui/StatusDot.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { PanelLeft, PanelRight, Search } from "@lucide/svelte";
</script>

<header class="command-bar">
  <div class="brand">
    <span class="monogram" aria-hidden="true">SB</span>
    <span class="wordmark">Second Brain</span>
  </div>

  <button class="search-trigger" onclick={() => workspace.openCommandPalette()} type="button">
    <Search size={14} strokeWidth={1.75} />
    <span class="placeholder">Search or run a command…</span>
    <span class="ui-kbd">⌘K</span>
  </button>

  <div class="actions">
    <Button variant="icon" title="Toggle vault" onclick={() => workspace.toggleLeft()}>
      <PanelLeft size={16} strokeWidth={1.75} />
    </Button>
    <Button variant="icon" title="Toggle inspector" onclick={() => workspace.toggleRight()}>
      <PanelRight size={16} strokeWidth={1.75} />
    </Button>
    <span class="status" class:online={connection.connected}>
      <StatusDot online={connection.connected} />
      <span class="status-text">
        {connection.connected ? `${connection.collectionCount}` : "Offline"}
      </span>
    </span>
  </div>
</header>

<style>
  .command-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    height: var(--shell-height);
    padding: 0 0.75rem;
    background: var(--pane-bg);
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .monogram {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    color: var(--text-muted);
  }

  .wordmark {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text);
  }

  .search-trigger {
    flex: 1;
    max-width: 420px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.65rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius);
    color: var(--text-faint);
    font-size: 0.75rem;
    text-align: left;
  }

  .search-trigger:hover {
    border-color: var(--border);
    color: var(--text-muted);
  }

  .placeholder {
    flex: 1;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-left: auto;
    flex-shrink: 0;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    margin-left: 0.35rem;
    padding: 0.2rem 0.5rem;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-faint);
    border: 1px solid var(--border-subtle);
    border-radius: 999px;
  }

  .status.online {
    color: var(--text-muted);
  }

  .status-text {
    min-width: 2ch;
  }
</style>