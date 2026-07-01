<script lang="ts">
  import Panel from "$lib/ui/Panel.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { FlaskConical, MessageSquare, FolderOpen } from "@lucide/svelte";
</script>

<Panel title="Second Brain" description="Your local research workspace">
  <div class="welcome">
    <button class="action-card" onclick={() => tabs.openResearchTab()}>
      <FlaskConical size={18} strokeWidth={1.75} />
      <span class="label">Run research</span>
      <span class="sub">Multi-agent report from your vault</span>
    </button>
    <button class="action-card" onclick={() => tabs.openQueryTab()}>
      <MessageSquare size={18} strokeWidth={1.75} />
      <span class="label">Quick query</span>
      <span class="sub">Fast RAG lookup with citations</span>
    </button>
    <button
      class="action-card"
      onclick={() => {
        workspace.toggleLeft();
        setTimeout(() => {
          document.querySelector<HTMLInputElement>("[data-vault-search]")?.focus();
        }, 50);
      }}
    >
      <FolderOpen size={18} strokeWidth={1.75} />
      <span class="label">Browse vault</span>
      <span class="sub">Open notes and PDFs from the sidebar</span>
    </button>
    <p class="hint">Press <span class="ui-kbd">⌘K</span> for commands</p>
  </div>
</Panel>

<style>
  .welcome {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .action-card {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    gap: 0.1rem 0.65rem;
    align-items: start;
    text-align: left;
    padding: 0.75rem 0.85rem;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius);
    color: var(--text);
    width: 100%;
  }

  .action-card :global(svg) {
    grid-row: span 2;
    color: var(--text-muted);
    margin-top: 0.1rem;
  }

  .action-card:hover {
    background: var(--surface-hover);
    border-color: var(--border);
  }

  .label {
    font-size: 0.8125rem;
    font-weight: 500;
  }

  .sub {
    font-size: 0.7rem;
    color: var(--text-faint);
  }

  .hint {
    margin-top: 0.5rem;
    font-size: 0.7rem;
    color: var(--text-faint);
    text-align: center;
  }
</style>