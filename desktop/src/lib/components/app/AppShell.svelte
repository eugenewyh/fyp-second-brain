<script lang="ts">
  import { onMount } from "svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import Sidebar from "./Sidebar.svelte";
  import DocumentView from "./DocumentView.svelte";
  import ChatHome from "./ChatHome.svelte";
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
    void connection.connect().then((ok) => {
      if (ok) void assistant.loadHarnessDefaults();
    });

    void workspace.ensureProjects().then(() => {
      tabs.pruneMissingSessions();
      if (workspace.activeTopicPath) {
        tabs.ensureWorkspaceView();
      } else if (Object.keys(assistant.sessions).length === 0 && app.isHome) {
        tabs.newWorkspaceChat();
      } else if (assistant.activeSessionId) {
        tabs.ensureSessionTab(assistant.activeSessionId);
      }
    });

    // Respect persisted knowledge-panel preference (default: open on first run)
    // workspace.knowledgePanelOpen is loaded from localStorage; leave as-is.

    let cleanup: (() => void) | undefined;
    void startVaultWatcher(() => {}).then((stop) => {
      cleanup = stop;
    });
    return () => cleanup?.();
  });

  $effect(() => {
    const id = assistant.activeSessionId;
    if (id) tabs.ensureSessionTab(id);
    tabs.pruneMissingSessions();
  });

  $effect(() => {
    if (!app.isMemory) workspace.memoryFilesOpen = false;
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
      tabs.newWorkspaceChat();
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
      workspace.toggleMemoryPanel();
      return;
    }
    if (e.key === "Escape") {
      if (workspace.commandPaletteOpen) {
        workspace.closeCommandPalette();
        return;
      }
      if (app.isMemory && app.documentPath) {
        app.closeDocument();
        e.preventDefault();
        return;
      }
      if (app.isMemory) {
        app.openHome();
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

<div class="shell">
  <div class="body" style="--sidebar-width: {sidebarWidth}px">
    <Sidebar />
    <PaneResizer
      onResize={onSidebarResize}
      onResizeEnd={onSidebarResizeEnd}
      testId="splitter-sidebar"
    />

    <div class="main-col">
      <div class="chrome-drag" data-tauri-drag-region aria-hidden="true"></div>
      <CommandPalette />
      <AppSheet />

      <div class="main-body">
        {#if app.isDocument}
          <DocumentView />
        {:else}
          <ChatHome />
        {/if}
      </div>
    </div>

    {#if workspace.knowledgePanelOpen && (app.isDocument || app.isDocumentPeek) && (!app.isMemory || workspace.memoryFilesOpen)}
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
