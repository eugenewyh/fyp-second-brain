<script lang="ts">
  interface Props {
    query: string;
    connected: boolean;
    loading: boolean;
    onSubmit: () => void;
    onLegacyMode?: (mode: "research" | "query" | "documents" | "settings") => void;
    activeLegacyMode?: "research" | "query" | "documents" | "settings";
  }

  let {
    query = $bindable(""),
    connected,
    loading,
    onSubmit,
    onLegacyMode,
    activeLegacyMode = "research",
  }: Props = $props();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmit();
    }
  }
</script>

<header class="command-bar" data-testid="command-bar">
  <div class="brand">
    <span class="logo">🧠</span>
    <span class="title">Ask Second Brain</span>
  </div>

  <div class="command-input">
    <input
      type="text"
      placeholder="Ask anything — ⌘↵ to run research"
      bind:value={query}
      onkeydown={handleKeydown}
      data-testid="command-bar-input"
    />
    <button
      class="btn-primary run-btn"
      onclick={onSubmit}
      disabled={loading || !connected || !query.trim()}
      data-testid="command-bar-submit"
    >
      {loading ? "Researching…" : "Run Research"}
    </button>
  </div>

  {#if onLegacyMode}
    <nav class="legacy-nav" aria-label="Legacy workspace modes">
      <button
        class="legacy-btn"
        class:active={activeLegacyMode === "research"}
        onclick={() => onLegacyMode("research")}
      >Research</button>
      <button
        class="legacy-btn"
        class:active={activeLegacyMode === "query"}
        onclick={() => onLegacyMode("query")}
      >Query</button>
      <button
        class="legacy-btn"
        class:active={activeLegacyMode === "documents"}
        onclick={() => onLegacyMode("documents")}
      >Docs</button>
      <button
        class="legacy-btn"
        class:active={activeLegacyMode === "settings"}
        onclick={() => onLegacyMode("settings")}
      >Settings</button>
    </nav>
  {/if}
</header>

<style>
  .command-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.65rem 1rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    min-height: 52px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .logo {
    font-size: 1.1rem;
  }

  .title {
    font-weight: 600;
    font-size: 0.95rem;
    white-space: nowrap;
  }

  .command-input {
    flex: 1;
    display: flex;
    gap: 0.5rem;
    min-width: 0;
  }

  .command-input input {
    flex: 1;
    min-width: 0;
  }

  .run-btn {
    flex-shrink: 0;
    white-space: nowrap;
  }

  .legacy-nav {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
  }

  .legacy-btn {
    background: transparent;
    color: var(--text-muted);
    padding: 0.35rem 0.55rem;
    font-size: 0.75rem;
    border-radius: 6px;
  }

  .legacy-btn:hover {
    background: var(--surface-hover);
    color: var(--text);
  }

  .legacy-btn.active {
    background: var(--surface-hover);
    color: var(--accent);
  }
</style>