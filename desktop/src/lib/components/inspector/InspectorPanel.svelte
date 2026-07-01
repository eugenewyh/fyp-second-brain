<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import ChatPane from "./ChatPane.svelte";
  import AgentLogPane from "./AgentLogPane.svelte";
  import BacklinksPane from "./BacklinksPane.svelte";
  import SourcesPane from "./SourcesPane.svelte";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { PanelRightClose } from "@lucide/svelte";

  const tabs = [
    { id: "chat" as const, label: "Chat" },
    { id: "agent" as const, label: "Agent" },
    { id: "backlinks" as const, label: "Links" },
    { id: "sources" as const, label: "Sources" },
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
    <SectionLabel>Inspector</SectionLabel>
    <Button variant="icon" title="Collapse" onclick={() => workspace.toggleRight()}>
      <PanelRightClose size={15} strokeWidth={1.75} />
    </Button>
  </div>

  <div class="actions">
    <Button
      variant="primary"
      onclick={researchDeeply}
      disabled={!connection.connected || research.loading}
    >
      Research deeply
    </Button>
  </div>

  <nav class="inspector-tabs">
    {#each tabs as tab}
      <button
        class="insp-tab"
        class:active={workspace.inspectorTab === tab.id}
        onclick={() => (workspace.inspectorTab = tab.id)}
      >
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
    background: var(--pane-bg);
    overflow: hidden;
  }

  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.55rem 0.65rem;
    border-bottom: 1px solid var(--border-subtle);
    min-height: 36px;
  }

  .actions {
    padding: 0.45rem 0.65rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .actions :global(.ui-btn.primary) {
    width: 100%;
    font-size: 0.75rem;
    padding: 0.4rem;
  }

  .inspector-tabs {
    display: flex;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .insp-tab {
    flex: 1;
    padding: 0.45rem 0.35rem;
    background: transparent;
    color: var(--text-faint);
    font-size: 0.7rem;
    font-weight: 500;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    margin-bottom: -1px;
  }

  .insp-tab:hover {
    color: var(--text-muted);
  }

  .insp-tab.active {
    color: var(--text);
    border-bottom-color: var(--accent);
  }

  .inspector-content {
    flex: 1;
    overflow: hidden;
  }
</style>