<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";

  let globalQuery = $state("");

  function onGlobalSubmit() {
    const q = globalQuery.trim();
    if (!q) return;
    research.runResearch(q);
    globalQuery = "";
  }

  function onGlobalKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") onGlobalSubmit();
  }
</script>

<header class="command-bar">
  <div class="brand">
    <span class="logo">🧠</span>
    <div>
      <h1>Second Brain</h1>
      <p class="subtitle">Workspace</p>
    </div>
  </div>

  <div class="global-search">
    <input
      bind:value={globalQuery}
      placeholder="Ask Second Brain…"
      onkeydown={onGlobalKeydown}
    />
    <button class="btn-primary search-btn" onclick={onGlobalSubmit} disabled={!connection.connected}>
      Research
    </button>
    <button class="btn-secondary kbd-btn" onclick={() => workspace.openCommandPalette()} title="Cmd/Ctrl+K">
      ⌘K
    </button>
  </div>

  <div class="actions">
    <button class="icon-btn" onclick={() => workspace.toggleLeft()} title="Toggle vault">
      ◧
    </button>
    <button class="icon-btn" onclick={() => workspace.toggleRight()} title="Toggle inspector">
      ◨
    </button>
    <span class="status-pill" class:online={connection.connected}>
      <span class="dot"></span>
      {connection.connected ? `${connection.collectionCount} chunks` : "Offline"}
    </span>
  </div>
</header>

<style>
  .command-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.55rem 0.85rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .logo {
    font-size: 1.25rem;
  }

  .brand h1 {
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.2;
  }

  .subtitle {
    font-size: 0.65rem;
    color: var(--text-muted);
  }

  .global-search {
    flex: 1;
    display: flex;
    gap: 0.4rem;
    max-width: 560px;
  }

  .search-btn,
  .kbd-btn {
    flex-shrink: 0;
    padding: 0.45rem 0.75rem;
    font-size: 0.8rem;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-left: auto;
    flex-shrink: 0;
  }

  .icon-btn {
    background: var(--surface-hover);
    color: var(--text-muted);
    padding: 0.35rem 0.5rem;
    font-size: 0.85rem;
    border: 1px solid var(--border);
  }

  .icon-btn:hover {
    color: var(--text);
    background: var(--border);
  }

  .status-pill {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    padding: 0.3rem 0.6rem;
    background: var(--bg);
    border-radius: 999px;
    border: 1px solid var(--border);
  }

  .status-pill.online {
    color: var(--success);
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--error);
  }

  .status-pill.online .dot {
    background: var(--success);
  }
</style>