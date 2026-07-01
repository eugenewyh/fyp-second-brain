<script lang="ts">
  import { onMount } from "svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import CommandBar from "./CommandBar.svelte";
  import CommandPalette from "./CommandPalette.svelte";
  import PaneResizer from "./PaneResizer.svelte";
  import VaultSidebar from "$lib/components/vault/VaultSidebar.svelte";
  import CenterWorkspace from "./CenterWorkspace.svelte";
  import InspectorPanel from "$lib/components/inspector/InspectorPanel.svelte";
  import { startVaultWatcher } from "$lib/vault/watcher";
  import Button from "$lib/ui/Button.svelte";
  import { PanelLeft, PanelRight } from "@lucide/svelte";

  onMount(() => {
    workspace.init();
    let cleanup: (() => void) | undefined;
    void startVaultWatcher(() => {}).then((stop) => {
      cleanup = stop;
    });
    return () => cleanup?.();
  });

  function onKeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      workspace.openCommandPalette();
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="workspace">
  <CommandBar />
  <CommandPalette />

  <div class="panes">
    {#if !workspace.leftCollapsed}
      <div class="pane left" style="width: {workspace.leftWidth}px">
        <VaultSidebar />
      </div>
      <PaneResizer onResize={(dx) => workspace.setLeftWidth(workspace.leftWidth + dx)} />
    {:else}
      <div class="rail">
        <Button variant="icon" title="Open vault" onclick={() => workspace.toggleLeft()}>
          <PanelLeft size={16} strokeWidth={1.75} />
        </Button>
      </div>
    {/if}

    <div class="pane center">
      <CenterWorkspace />
    </div>

    {#if !workspace.rightCollapsed}
      <PaneResizer onResize={(dx) => workspace.setRightWidth(workspace.rightWidth - dx)} />
      <div class="pane right" style="width: {workspace.rightWidth}px">
        <InspectorPanel />
      </div>
    {:else}
      <div class="rail">
        <Button variant="icon" title="Open inspector" onclick={() => workspace.toggleRight()}>
          <PanelRight size={16} strokeWidth={1.75} />
        </Button>
      </div>
    {/if}
  </div>
</div>

<style>
  .workspace {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    background: var(--bg);
  }

  .panes {
    display: flex;
    flex: 1;
    min-height: 0;
  }

  .pane {
    flex-shrink: 0;
    overflow: hidden;
    border-right: 1px solid var(--border-subtle);
  }

  .pane.right {
    border-right: none;
    border-left: 1px solid var(--border-subtle);
  }

  .pane.center {
    flex: 1;
    min-width: 320px;
    border-right: none;
    background: var(--bg-elevated);
  }

  .rail {
    width: 32px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 0.5rem;
    background: var(--pane-bg);
    border-right: 1px solid var(--border-subtle);
  }

  .panes > .rail:last-child {
    border-right: none;
    border-left: 1px solid var(--border-subtle);
  }
</style>