<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import ChatPane from "./ChatPane.svelte";
  import AgentLogPane from "./AgentLogPane.svelte";
  import BacklinksPane from "./BacklinksPane.svelte";
  import SourcesPane from "./SourcesPane.svelte";

  const tabs = [
    { id: "chat" as const, label: "Chat", icon: "💬" },
    { id: "agent" as const, label: "Agent", icon: "⚙️" },
    { id: "backlinks" as const, label: "Links", icon: "🔗" },
    { id: "sources" as const, label: "Sources", icon: "📚" },
  ];

  function researchDeeply() {
    const q =
      workspace.selectedText.trim() ||
      workspace.activeNotePath?.split("/").pop()?.replace(/\.md$/, "") ||
      "";
    if (q) research.runResearch(q);
    workspace.inspectorTab = "agent";
  }
</script>

<aside class="inspector">
  <div class="header">
    <h2>Inspector</h2>
    <button class="collapse-btn" onclick={() => workspace.toggleRight()} title="Collapse">▶</button>
  </div>

  <div class="actions">
    <button
      class="btn-primary deep-btn"
      onclick={researchDeeply}
      disabled={!connection.connected || research.loading}
    >
      Research this deeply
    </button>
  </div>

  <nav class="inspector-tabs">
    {#each tabs as tab}
      <button
        class="insp-tab"
        class:active={workspace.inspectorTab === tab.id}
        onclick={() => (workspace.inspectorTab = tab.id)}
      >
        <span>{tab.icon}</span>
        {tab.label}
      </button>
    {/each}
  </nav>

  <div class="inspector-content">
    {#if workspace.inspectorTab === "chat"}
      <ChatPane />
    {:else if workspace.inspectorTab === "agent"}
      <AgentLogPane />
    {:else if workspace.inspectorTab === "backlinks"}
      <BacklinksPane />
    {:else}
      <SourcesPane />
    {/if}
  </div>
</aside>

<style>
  .inspector {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--pane-bg, var(--surface));
    overflow: hidden;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.65rem 0.75rem;
    border-bottom: 1px solid var(--border);
  }

  .header h2 {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .collapse-btn {
    background: transparent;
    color: var(--text-muted);
    padding: 0.2rem 0.4rem;
    font-size: 0.75rem;
  }

  .actions {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border);
  }

  .deep-btn {
    width: 100%;
    font-size: 0.8rem;
    padding: 0.45rem;
  }

  .inspector-tabs {
    display: flex;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .insp-tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.15rem;
    padding: 0.45rem 0.25rem;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.65rem;
    border-radius: 0;
  }

  .insp-tab.active {
    color: var(--accent);
    border-bottom: 2px solid var(--accent);
  }

  .inspector-content {
    flex: 1;
    overflow: hidden;
  }
</style>