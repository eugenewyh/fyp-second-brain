<script lang="ts">
  import { onMount } from "svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import MemorySidebar from "./MemorySidebar.svelte";
  import DocumentView from "./DocumentView.svelte";
  import MemoryHome from "./MemoryHome.svelte";
  import KnowledgePanel from "./KnowledgePanel.svelte";
  import AppSheet from "./AppSheet.svelte";
  import NewProjectModal from "./NewProjectModal.svelte";
  import CommandPalette from "$lib/components/workspace/CommandPalette.svelte";
  import PaneResizer from "$lib/components/workspace/PaneResizer.svelte";
  import { startVaultWatcher } from "$lib/vault/watcher";
  import {
    clampSidebarWidth,
    loadSidebarWidth,
    saveSidebarWidth,
  } from "$lib/workspace/layout-prefs";
  import { authSession } from "$lib/auth/auth-session.svelte";
  import { currentUser } from "$lib/auth/client";

  let sidebarWidth = $state(loadSidebarWidth());

  function onSidebarResize(delta: number) {
    sidebarWidth = clampSidebarWidth(sidebarWidth + delta);
  }

  function onSidebarResizeEnd() {
    saveSidebarWidth(sidebarWidth);
  }

  onMount(() => {
    authSession.hydrate();
    void currentUser().catch(() => {});

    workspace.init();
    void connection.connect();
    void workspace.ensureProjects();

    let cleanup: (() => void) | undefined;
    void startVaultWatcher(() => {})
      .then((stop) => {
        cleanup = stop;
      })
      .catch(() => {
        /* Browser / missing Tauri IPC — UI still works without live vault watch */
      });
    return () => cleanup?.();
  });

  function onKeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      workspace.openCommandPalette();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "b") {
      e.preventDefault();
      workspace.toggleKnowledgePanel();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "n") {
      e.preventDefault();
      app.openNewProject();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "l") {
      e.preventDefault();
      workspace.openLibrary();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "u") {
      e.preventDefault();
      app.openSheet("ingest");
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "g") {
      e.preventDefault();
      if (!app.isMemory) app.openMemory();
      return;
    }
    if (e.key === "Escape") {
      if (workspace.commandPaletteOpen) {
        workspace.closeCommandPalette();
        return;
      }
      if (app.documentPath) {
        app.closeDocument();
        e.preventDefault();
        return;
      }
      if (
        app.handleEscapePanel(workspace.knowledgePanelOpen, () =>
          workspace.setKnowledgePanel(false),
        )
      ) {
        e.preventDefault();
      }
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="shell" data-chrome-layer>
  <div class="body" style="--sidebar-width: {sidebarWidth}px">
    <MemorySidebar />
    <PaneResizer
      onResize={onSidebarResize}
      onResizeEnd={onSidebarResizeEnd}
      testId="splitter-sidebar"
    />

    <div class="main-col" data-chrome-layer>
      <div class="chrome-drag" data-tauri-drag-region aria-hidden="true"></div>
      <CommandPalette />
      <AppSheet />

      <div class="main-body">
        {#if app.isDocument}
          <DocumentView />
        {:else}
          <MemoryHome />
        {/if}
      </div>
    </div>

    {#if workspace.knowledgePanelOpen && (app.isDocument || app.isDocumentPeek) && (!app.isMemory || workspace.memoryFilesOpen || app.isDocumentPeek)}
      <KnowledgePanel />
    {/if}
  </div>

  <NewProjectModal />
</div>

<style>
  .shell {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
    background: var(--pane-bg);
  }

  .body {
    flex: 1;
    min-height: 0;
    display: flex;
    overflow: hidden;
  }

  .main-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
    position: relative;
    background: var(--bg);
  }

  /* Overlay inset: drag to move the window. Columns paint through this band. */
  .chrome-drag {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: var(--titlebar-height);
    z-index: 4;
    -webkit-app-region: drag;
    app-region: drag;
  }

  .main-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
</style>
