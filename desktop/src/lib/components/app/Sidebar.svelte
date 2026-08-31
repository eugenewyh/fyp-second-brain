<script lang="ts">
  import { onMount } from "svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { groupSessionsByWorkspace } from "$lib/assistant/workspace-chats";
  import { deleteProjectFolder, updateProjectFolder } from "$lib/vault/load";
  import { pathsMatch } from "$lib/assistant/workspace-chats";
  import { authSession } from "$lib/auth/auth-session.svelte";
  import WorkspaceChatTree from "./WorkspaceChatTree.svelte";
  import SectionLabel from "$lib/ui/SectionLabel.svelte";
  import { Plus, Settings, CalendarClock, Network, Send } from "@lucide/svelte";

  let search = $state("");

  const iconSize = 16;
  const iconStroke = 1.75;

  const workspaceGroups = $derived(
    groupSessionsByWorkspace(
      assistant.listChannelSessions(),
      workspace.projectFolders,
      search,
      workspace.pinnedPaths,
    ),
  );

  async function refreshProjects() {
    await workspace.syncProjectsFromDisk();
  }

  function ensureTopic() {
    if (!workspace.activeTopicPath) {
      const first = workspace.projectFolders[0];
      if (first) workspace.setActiveTopic(first.path);
    }
  }

  function openSettings() {
    app.openSettings("appearance");
  }

  function openSignIn() {
    app.openSettings("account");
  }

  function openWatch() {
    ensureTopic();
    app.openWatch();
  }

  const accountLabel = $derived(authSession.label);
  const accountInitial = $derived(authSession.initial);
  const signedIn = $derived(authSession.signedIn);

  function openMemory() {
    app.openMemory();
  }

  function newChat() {
    ensureTopic();
    tabs.newWorkspaceChat();
  }

  function newWorkspace() {
    app.openNewProject();
  }

  function openSession(sessionId: string) {
    tabs.openSession(sessionId);
  }

  function newChatInWorkspace(path: string) {
    tabs.newChatInWorkspace(path);
  }

  function deleteSession(sessionId: string) {
    const s = assistant.sessions[sessionId];
    if (!s) return;
    const label = s.title || "this chat";
    const ok = window.confirm(`Delete chat “${label}”?`);
    if (!ok) return;
    const path = s.projectPath;
    assistant.deleteSession(sessionId);
    tabs.pruneMissingSessions();

    const remaining = path
      ? assistant
          .listChannelSessions()
          .filter((x) => pathsMatch(x.projectPath, path))
      : [];

    if (remaining[0]) {
      tabs.openSession(remaining[0].id);
      return;
    }

    // Last chat in this workspace — leave empty (do not auto-create a replacement)
    if (path) workspace.setActiveTopic(path);
    assistant.clearActiveSession();
    app.openHome();
  }

  async function renameWorkspace(path: string, name: string) {
    try {
      const newPath = await updateProjectFolder(path, { name });
      if (newPath !== path) {
        assistant.rebindProjectPath(path, newPath);
        workspace.rebindTopicPath(path, newPath);
      }
      workspace.requestVaultRefresh();
      await workspace.syncProjectsFromDisk();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Could not rename workspace");
    }
  }

  async function deleteWorkspace(path: string, name: string): Promise<boolean> {
    const busy = assistant
      .listChannelSessions()
      .some((s) => pathsMatch(s.projectPath, path) && assistant.sessionBusy(s.id));
    const ok = window.confirm(
      busy
        ? `“${name}” is still filing notes into memory. Cancel that and delete the workspace? This cannot be undone.`
        : `Delete workspace “${name}”? This removes its folder and cannot be undone.`,
    );
    if (!ok) return false;
    try {
      const wasActive = pathsMatch(workspace.activeTopicPath, path);

      // Stop Remember/Ask jobs first — otherwise they rewrite the folder and it “comes back”.
      assistant.purgeProjectSessions(path);
      workspace.unpin(path);

      await deleteProjectFolder(path);
      // Race: in-flight server writes may recreate the dir after abort; sweep once more.
      await new Promise((r) => setTimeout(r, 400));
      await deleteProjectFolder(path);

      workspace.requestVaultRefresh();
      await workspace.syncProjectsFromDisk();

      if (wasActive) {
        const next = workspace.projectFolders[0]?.path ?? null;
        if (next) tabs.openWorkspace(next);
        else {
          workspace.setActiveTopic(null);
          app.openHome();
        }
      }
      return true;
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Could not delete workspace");
      return false;
    }
  }

  onMount(() => {
    void refreshProjects();
  });

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void refreshProjects();
  });
</script>

<aside class="sidebar" aria-label="Navigation">
  <div class="titlebar" data-tauri-drag-region></div>
  <nav class="nav-top">
    <button type="button" class="nav-item" onclick={newChat}>
      <Send size={iconSize} strokeWidth={iconStroke} />
      New Chat
    </button>
    <button
      type="button"
      class="nav-item"
      class:active={app.isMemory}
      onclick={openMemory}
    >
      <Network size={iconSize} strokeWidth={iconStroke} />
      Memory
    </button>
    <button
      type="button"
      class="nav-item"
      class:active={app.isWatch}
      onclick={openWatch}
    >
      <CalendarClock size={iconSize} strokeWidth={iconStroke} />
      Scheduled Research
    </button>
  </nav>

  <div class="search-wrap">
    <input
      class="search"
      type="search"
      placeholder="Search workspaces…"
      bind:value={search}
    />
  </div>

  <div class="section-head">
    <SectionLabel>Workspaces</SectionLabel>
    <button
      type="button"
      class="section-add"
      aria-label="New workspace"
      title="New workspace"
      onclick={newWorkspace}
    >
      <Plus size={14} strokeWidth={2} />
    </button>
  </div>

  <div class="sessions ui-scroll">
    {#if workspaceGroups.length === 0}
      <p class="empty">No workspaces yet</p>
    {:else if search.trim() &&
      workspaceGroups.every(
        (g) =>
          !g.name.toLowerCase().includes(search.trim().toLowerCase()) &&
          g.sessions.length === 0,
      )}
      <p class="empty">No matching workspaces</p>
    {:else}
      <WorkspaceChatTree
        groups={workspaceGroups}
        {search}
        activeWorkspacePath={workspace.activeTopicPath}
        activeSessionId={assistant.activeSessionId}
        onOpenSession={openSession}
        onNewChat={newChatInWorkspace}
        onDeleteSession={deleteSession}
        onEditWorkspace={(path) => app.openEditProject(path)}
        onRenameWorkspace={renameWorkspace}
        onDeleteWorkspace={deleteWorkspace}
        onTogglePin={(path) => workspace.togglePin(path)}
      />
    {/if}
  </div>

  <div class="footer">
    <div class="account-row">
      {#if signedIn}
        <button type="button" class="account" onclick={openSignIn} title={accountLabel}>
          <span class="avatar" aria-hidden="true">{accountInitial}</span>
          <span class="account-name">{accountLabel}</span>
        </button>
      {:else}
        <button type="button" class="account sign-in" onclick={openSignIn}>
          Sign in
        </button>
      {/if}
      <button
        type="button"
        class="settings-icon"
        class:active={app.sheet === "settings"}
        aria-label="Settings"
        title="Settings"
        onclick={openSettings}
      >
        <Settings size={iconSize} strokeWidth={iconStroke} />
      </button>
    </div>
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--pane-bg);
    border-right: 1px solid var(--border-subtle);
  }

  .titlebar {
    height: var(--titlebar-height);
    flex-shrink: 0;
    -webkit-app-region: drag;
    app-region: drag;
  }

  .sidebar :global(button),
  .sidebar :global(input) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .nav-top {
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
    padding: 0.15rem 0.5rem 0.25rem;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: var(--type-nav-size);
    font-weight: var(--type-nav-weight);
    line-height: var(--type-nav-leading);
    letter-spacing: var(--type-nav-tracking);
    min-height: 32px;
    padding: 0.3rem var(--space-2);
    border-radius: var(--radius-feedback);
    cursor: pointer;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
  }

  .nav-item:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .nav-item.active {
    background: var(--selection-bg);
    color: var(--text);
  }

  .search-wrap {
    padding: 0.35rem 0.65rem 0.55rem;
  }

  .search {
    width: 100%;
    height: 32px;
    padding: 0 0.6rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
    color: var(--text);
    font-size: var(--type-body-sm-size);
    font-weight: var(--type-body-sm-weight);
    line-height: var(--type-body-sm-leading);
  }

  .search:focus {
    outline: none;
    border-color: var(--border-active);
  }

  .section-head {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    padding: 0.15rem 0.55rem 0.35rem 0.85rem;
  }

  .section-add {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    min-width: 22px;
    min-height: 22px;
    padding: 0;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
  }

  .section-add:hover,
  .section-add:focus-visible {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .section-add:focus-visible {
    outline: 1px solid var(--focus-ring);
    outline-offset: 1px;
  }

  .sessions {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 0 0.3rem 0.5rem;
  }

  .empty {
    margin: 0.5rem 0.45rem;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .footer {
    flex-shrink: 0;
    padding: 0.35rem 0.5rem 0.55rem;
    border-top: 1px solid var(--border-subtle);
  }

  .account-row {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    min-width: 0;
  }

  .account {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    text-align: left;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    min-height: 32px;
    padding: 0.3rem 0.45rem;
    border-radius: var(--radius-feedback);
    cursor: pointer;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
  }

  .account:hover,
  .account.sign-in:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .account.sign-in {
    color: var(--text);
  }

  .avatar {
    flex-shrink: 0;
    width: 1.35rem;
    height: 1.35rem;
    border-radius: var(--radius-full);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    background: var(--control-fill);
    color: var(--text);
  }

  .account-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .settings-icon {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
  }

  .settings-icon:hover,
  .settings-icon.active {
    background: var(--chrome-action-hover);
    color: var(--text);
  }
</style>
