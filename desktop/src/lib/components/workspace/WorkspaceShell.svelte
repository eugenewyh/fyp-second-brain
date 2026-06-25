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
      <button class="rail" onclick={() => workspace.toggleLeft()} title="Open vault">◧</button>
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
      <button class="rail" onclick={() => workspace.toggleRight()} title="Open inspector">◨</button>
    {/if}
  </div>
</div>

<style>
  .workspace {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .panes {
    display: flex;
    flex: 1;
    min-height: 0;
  }

  .pane {
    flex-shrink: 0;
    overflow: hidden;
    border-right: 1px solid var(--border);
  }

  .pane.right {
    border-right: none;
    border-left: 1px solid var(--border);
  }

  .pane.center {
    flex: 1;
    min-width: 320px;
    border-right: none;
  }

  .rail {
    width: 28px;
    flex-shrink: 0;
    background: var(--surface);
    color: var(--text-muted);
    border: none;
    border-right: 1px solid var(--border);
    font-size: 0.85rem;
    padding: 0;
  }

  .rail:hover {
    background: var(--surface-hover);
    color: var(--text);
  }
</style>