<script lang="ts">
  import { tick } from "svelte";
  import { fade, fly } from "svelte/transition";
  import { app } from "$lib/stores/app.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import {
    formatRelativeTime,
    pathsMatch,
    type WorkspaceGroup,
    type WorkspaceSession,
  } from "$lib/assistant/workspace-chats";
  import { ThinkingOrb } from "svelte-thinking-orbs";
  import { ChevronRight, Folder, FolderOpen, MessageSquare, Pin, Plus, X } from "@lucide/svelte";

  interface Props {
    groups: WorkspaceGroup[];
    search?: string;
    activeWorkspacePath: string | null;
    activeSessionId?: string | null;
    onOpenSession: (sessionId: string) => void;
    onNewChat: (path: string) => void;
    onDeleteSession?: (sessionId: string) => void;
    onEditWorkspace: (path: string) => void;
    onRenameWorkspace: (path: string, name: string) => Promise<void> | void;
    /** Returns true when the workspace was deleted. */
    onDeleteWorkspace: (path: string, name: string) => Promise<boolean> | boolean;
    onTogglePin: (path: string) => void;
  }

  let {
    groups,
    search = "",
    activeWorkspacePath,
    activeSessionId = null,
    onOpenSession,
    onNewChat,
    onDeleteSession,
    onEditWorkspace,
    onRenameWorkspace,
    onDeleteWorkspace,
    onTogglePin,
  }: Props = $props();

  let menu = $state<
    | { kind: "workspace"; path: string; x: number; y: number }
    | { kind: "session"; sessionId: string; path: string; x: number; y: number }
    | null
  >(null);
  let menuEl = $state<HTMLDivElement | null>(null);
  let renamingPath = $state<string | null>(null);
  let renameDraft = $state("");
  let renameEl = $state<HTMLInputElement | null>(null);
  let renameBusy = $state(false);
  let pinFlashPath = $state<string | null>(null);
  let pinFlashTimer: ReturnType<typeof setTimeout> | null = null;
  let actionBusy = $state(false);
  /** Expanded workspace paths (normalized). */
  let expanded = $state<Set<string>>(new Set());
  /** Last workspace we auto-expanded (so collapse is not overridden). */
  let autoExpandedPath = $state<string | null>(null);

  function normPath(path: string): string {
    return path.replace(/[/\\]+$/, "").toLowerCase();
  }

  function isExpanded(path: string): boolean {
    return expanded.has(normPath(path));
  }

  function setExpanded(path: string, open: boolean) {
    const key = normPath(path);
    const next = new Set(expanded);
    if (open) next.add(key);
    else next.delete(key);
    expanded = next;
  }

  function toggleExpanded(path: string, e?: MouseEvent) {
    e?.preventDefault();
    e?.stopPropagation();
    setExpanded(path, !isExpanded(path));
  }

  /** Auto-expand when switching to a workspace; do not re-open after user collapse. */
  $effect(() => {
    const path = activeWorkspacePath;
    if (!path) return;
    const key = normPath(path);
    if (autoExpandedPath === key) return;
    autoExpandedPath = key;
    setExpanded(path, true);
  });

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      },
    };
  }

  function closeMenu() {
    menu = null;
  }

  function openWorkspaceMenu(path: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (actionBusy) return;
    renamingPath = null;
    menu = { kind: "workspace", path, x: e.clientX, y: e.clientY };
  }

  function openSessionMenu(sessionId: string, path: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (actionBusy) return;
    menu = { kind: "session", sessionId, path, x: e.clientX, y: e.clientY };
  }

  function runAfterMenu(action: () => void) {
    closeMenu();
    requestAnimationFrame(() => {
      requestAnimationFrame(action);
    });
  }

  function sessionRunning(session: WorkspaceSession): boolean {
    if (assistant.sessionBusy(session.id)) return true;
    const s = assistant.sessions[session.id];
    return !!s?.turns.some(
      (t) =>
        (t.kind === "research" &&
          (t.status === "running" || t.status === "awaiting_plan")) ||
        (t.kind === "digest" && t.status === "running"),
    );
  }

  function visibleGroups(): WorkspaceGroup[] {
    const q = search.trim().toLowerCase();
    if (!q) return groups;
    return groups.filter(
      (g) =>
        g.name.toLowerCase().includes(q) ||
        g.sessions.some((s) => (s.title || "").toLowerCase().includes(q)),
    );
  }

  function filteredSessions(group: WorkspaceGroup): WorkspaceSession[] {
    const q = search.trim().toLowerCase();
    if (!q) return group.sessions;
    if (group.name.toLowerCase().includes(q)) return group.sessions;
    return group.sessions.filter((s) => (s.title || "").toLowerCase().includes(q));
  }

  async function startRename(path: string, name: string) {
    closeMenu();
    renamingPath = path;
    renameDraft = name;
    await tick();
    renameEl?.focus();
    renameEl?.select();
  }

  async function commitRename() {
    if (!renamingPath || renameBusy) return;
    const path = renamingPath;
    const name = renameDraft.trim();
    renamingPath = null;
    if (!name) return;
    const group = groups.find((g) => pathsMatch(g.path, path));
    if (group && group.name === name) return;
    renameBusy = true;
    try {
      await onRenameWorkspace(path, name);
    } finally {
      renameBusy = false;
    }
  }

  function cancelRename() {
    renamingPath = null;
  }

  function flashPin(path: string) {
    if (pinFlashTimer) clearTimeout(pinFlashTimer);
    pinFlashPath = path;
    pinFlashTimer = setTimeout(() => {
      pinFlashPath = null;
      pinFlashTimer = null;
    }, 420);
  }

  function editWorkspace(path: string) {
    runAfterMenu(() => onEditWorkspace(path));
  }

  function togglePin(path: string) {
    runAfterMenu(() => {
      onTogglePin(path);
      flashPin(path);
    });
  }

  function newChat(path: string) {
    runAfterMenu(() => {
      setExpanded(path, true);
      onNewChat(path);
    });
  }

  async function deleteWorkspace(path: string, name: string) {
    if (actionBusy) return;
    actionBusy = true;
    closeMenu();
    try {
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      await onDeleteWorkspace(path, name);
    } finally {
      actionBusy = false;
    }
  }

  function deleteSession(sessionId: string) {
    runAfterMenu(() => onDeleteSession?.(sessionId));
  }

  $effect(() => {
    if (!menu) return;
    const onPtr = (e: PointerEvent) => {
      if (menuEl?.contains(e.target as Node)) return;
      closeMenu();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeMenu();
    };
    const bindId = window.setTimeout(() => {
      window.addEventListener("pointerdown", onPtr, true);
      window.addEventListener("keydown", onKey, true);
    }, 0);
    return () => {
      window.clearTimeout(bindId);
      window.removeEventListener("pointerdown", onPtr, true);
      window.removeEventListener("keydown", onKey, true);
    };
  });

  $effect(() => {
    if (!menu || !menuEl) return;
    const pad = 8;
    const rect = menuEl.getBoundingClientRect();
    let x = menu.x;
    let y = menu.y;
    if (x + rect.width > window.innerWidth - pad) {
      x = Math.max(pad, window.innerWidth - rect.width - pad);
    }
    if (y + rect.height > window.innerHeight - pad) {
      y = Math.max(pad, window.innerHeight - rect.height - pad);
    }
    if (x !== menu.x || y !== menu.y) {
      menu = { ...menu, x, y };
    }
  });
</script>

<ul class="list">
  {#each visibleGroups() as group (group.path)}
    {@const isSelectedWorkspace = pathsMatch(group.path, activeWorkspacePath)}
    {@const renaming = pathsMatch(renamingPath, group.path)}
    {@const pinFlash = pathsMatch(pinFlashPath, group.path)}
    {@const open = isExpanded(group.path)}
    {@const chats = filteredSessions(group)}
    {@const workspaceRowActive =
      isSelectedWorkspace &&
      (app.isWatch || (app.isHome && !activeSessionId))}
    <li
      class="group"
      class:pin-flash={pinFlash}
      in:fly={{ y: -6, duration: 150 }}
      out:fade={{ duration: 160 }}
    >
      <div
        class="workspace"
        class:active={workspaceRowActive}
        class:pinned={group.pinned}
        class:pin-pop={pinFlash && group.pinned}
        role={renaming ? undefined : "button"}
        tabindex={renaming ? -1 : 0}
        onclick={() => {
          if (renaming) return;
          toggleExpanded(group.path);
        }}
        onkeydown={(e) => {
          if (renaming) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleExpanded(group.path);
          }
        }}
        oncontextmenu={(e) => openWorkspaceMenu(group.path, e)}
        title={group.name}
        aria-expanded={open}
      >
        <span class="lead-icon workspace-lead" aria-hidden="true">
          <span class="lead-mark default" class:is-open={open}>
            <span class="folder-state closed">
              <Folder size={13} strokeWidth={1.75} />
            </span>
            <span class="folder-state open">
              <FolderOpen size={13} strokeWidth={1.75} />
            </span>
          </span>
          <span class="lead-mark chevron" class:open>
            <ChevronRight size={12} strokeWidth={2} />
          </span>
        </span>
        {#if renaming}
          <input
            class="rename-input"
            bind:this={renameEl}
            bind:value={renameDraft}
            aria-label="Rename workspace"
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void commitRename();
              } else if (e.key === "Escape") {
                e.preventDefault();
                cancelRename();
              }
            }}
            onblur={() => void commitRename()}
          />
        {:else}
          <span class="label">{group.name}</span>
          {#if group.pinned}
            <span class="pin-mark" class:pop={pinFlash} aria-label="Pinned">
              <Pin size={11} strokeWidth={2} />
            </span>
          {/if}
        {/if}
        <button
          type="button"
          class="new-chat-btn"
          title="New chat"
          aria-label="New chat in {group.name}"
          onclick={(e) => {
            e.stopPropagation();
            newChat(group.path);
          }}
        >
          <Plus size={12} strokeWidth={2.25} />
        </button>
      </div>

      <div
        class="chats-panel"
        class:open={open && !renaming}
        aria-hidden={!open || renaming}
      >
        <ul class="chats">
          {#each chats as session (session.id)}
            {@const chatActive = session.id === activeSessionId && app.isHome}
            {@const chatRun = sessionRunning(session)}
            <li>
              <div class="chat-row" class:active={chatActive} class:running={chatRun}>
                <button
                  type="button"
                  class="chat"
                  class:active={chatActive}
                  class:running={chatRun}
                  onclick={() => onOpenSession(session.id)}
                  oncontextmenu={(e) => openSessionMenu(session.id, group.path, e)}
                  title={session.title}
                >
                  <span class="lead-icon" class:live={chatRun} aria-hidden="true">
                    {#if chatRun}
                      <span class="orb-slot">
                        <ThinkingOrb
                          state="connecting"
                          size={20}
                          theme="auto"
                          aria-label="Working"
                        />
                      </span>
                    {:else}
                      <MessageSquare size={13} strokeWidth={1.75} />
                    {/if}
                  </span>
                  <span class="label">{session.title || "New Chat"}</span>
                  <span class="meta">{formatRelativeTime(session.updatedAt)}</span>
                </button>
                {#if onDeleteSession}
                  <button
                    type="button"
                    class="chat-del"
                    title="Delete chat"
                    aria-label="Delete chat"
                    onclick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                  >
                    <X size={12} strokeWidth={2.25} />
                  </button>
                {/if}
              </div>
            </li>
          {:else}
            <li class="empty-chats">No chats yet</li>
          {/each}
        </ul>
      </div>
    </li>
  {/each}
</ul>

{#if menu?.kind === "workspace"}
  {@const group = groups.find((g) => pathsMatch(g.path, menu.path))}
  {#if group}
    <div
      class="menu"
      use:portal
      bind:this={menuEl}
      role="menu"
      style:left={`${menu.x}px`}
      style:top={`${menu.y}px`}
      onpointerdown={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        role="menuitem"
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          newChat(group.path);
        }}
      >
        New chat
      </button>
      <button
        type="button"
        role="menuitem"
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          editWorkspace(group.path);
        }}
      >
        Edit workspace
      </button>
      <button
        type="button"
        role="menuitem"
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          void startRename(group.path, group.name);
        }}
      >
        Rename
      </button>
      <button
        type="button"
        role="menuitem"
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          togglePin(group.path);
        }}
      >
        {group.pinned ? "Unpin" : "Pin"}
      </button>
      <button
        type="button"
        role="menuitem"
        class="danger"
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          void deleteWorkspace(group.path, group.name);
        }}
      >
        Delete workspace
      </button>
    </div>
  {/if}
{:else if menu?.kind === "session"}
  <div
    class="menu"
    use:portal
    bind:this={menuEl}
    role="menu"
    style:left={`${menu.x}px`}
    style:top={`${menu.y}px`}
    onpointerdown={(e) => e.stopPropagation()}
  >
    <button
      type="button"
      role="menuitem"
      onpointerdown={(e) => {
        e.preventDefault();
        e.stopPropagation();
        runAfterMenu(() => onOpenSession(menu.sessionId));
      }}
    >
      Open chat
    </button>
    <button
      type="button"
      role="menuitem"
      onpointerdown={(e) => {
        e.preventDefault();
        e.stopPropagation();
        newChat(menu.path);
      }}
    >
      New chat
    </button>
    {#if onDeleteSession}
      <button
        type="button"
        role="menuitem"
        class="danger"
        onpointerdown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          deleteSession(menu.sessionId);
        }}
      >
        Delete chat
      </button>
    {/if}
  </div>
{/if}

<style>
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    font-family: inherit;
    font-size: var(--type-nav-size);
    font-weight: var(--type-nav-weight);
    letter-spacing: var(--type-nav-tracking);
    line-height: var(--type-nav-leading);
  }

  li.group {
    display: flex;
    flex-direction: column;
    gap: 1px;
    position: relative;
    transition:
      opacity var(--dur-med) var(--ease-out),
      transform var(--dur-med) var(--ease-out);
  }

  li.pin-flash {
    animation: pin-row-flash var(--dur-expand) var(--ease-out);
  }

  .workspace,
  .chat {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    width: 100%;
    box-sizing: border-box;
    min-width: 0;
    min-height: 30px;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-muted);
    font: inherit;
    font-size: var(--type-nav-size);
    font-weight: inherit;
    letter-spacing: inherit;
    line-height: inherit;
    text-align: left;
    cursor: pointer;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out),
      transform var(--dur-med) var(--ease-out);
  }

  .workspace {
    padding: 0 0.4rem 0 0.35rem;
    user-select: none;
  }

  .workspace:focus,
  .workspace:focus-visible {
    outline: none;
  }

  .workspace:hover,
  .chat:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .workspace:hover .new-chat-btn {
    opacity: 1;
  }

  .workspace.active,
  .chat.active {
    background: var(--selection-bg);
    color: var(--text);
  }

  .workspace.pin-pop {
    transform: translateX(2px);
  }

  .workspace-lead {
    position: relative;
    width: 16px;
    height: 16px;
  }

  .workspace-lead .lead-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    color: var(--text-faint);
    transition:
      color var(--dur-control) var(--ease-out),
      transform var(--dur-expand) var(--ease-out),
      opacity var(--dur-med) var(--ease-out);
  }

  .workspace-lead .lead-mark.chevron {
    display: none;
  }

  .workspace-lead .lead-mark.chevron.open {
    transform: rotate(90deg);
  }

  .workspace-lead .lead-mark.default {
    position: relative;
  }

  .workspace-lead .folder-state {
    position: absolute;
    inset: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition:
      opacity var(--dur-expand) var(--ease-out),
      transform var(--dur-expand) var(--ease-out);
  }

  .workspace-lead .folder-state.closed {
    opacity: 1;
    transform: scale(1);
  }

  .workspace-lead .folder-state.open {
    opacity: 0;
    transform: scale(0.88) translateY(1px);
  }

  .workspace-lead .lead-mark.default.is-open .folder-state.closed {
    opacity: 0;
    transform: scale(0.88) translateY(-1px);
  }

  .workspace-lead .lead-mark.default.is-open .folder-state.open {
    opacity: 1;
    transform: scale(1) translateY(0);
  }

  .workspace:hover .workspace-lead .lead-mark.default {
    display: none;
  }

  .workspace:hover .workspace-lead .lead-mark.chevron {
    display: inline-flex;
  }

  .lead-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    color: var(--text-faint);
    flex-shrink: 0;
  }

  .lead-icon.live {
    color: var(--accent-live, var(--text));
  }

  .workspace:hover .workspace-lead .lead-mark,
  .workspace.active .workspace-lead .lead-mark,
  .workspace:hover .lead-icon,
  .chat:hover .lead-icon,
  .chat.active .lead-icon {
    color: var(--text-muted);
  }

  .chat.running .lead-icon,
  .chat.running:hover .lead-icon,
  .chat.running.active .lead-icon {
    color: var(--accent-live, var(--text));
  }

  .orb-slot {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  .label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font: inherit;
    font-weight: inherit;
  }

  .meta {
    flex-shrink: 0;
    font: inherit;
    font-size: var(--text-sm);
    font-weight: inherit;
    color: var(--text-faint);
    font-variant-numeric: tabular-nums;
    letter-spacing: 0;
  }

  .pin-mark {
    display: inline-flex;
    color: var(--text-faint);
    flex-shrink: 0;
    transform-origin: center;
  }

  .pin-mark.pop {
    color: var(--accent-live);
    animation: pin-pop var(--dur-expand) var(--ease-out);
  }

  .new-chat-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    min-width: 20px;
    min-height: 20px;
    padding: 0;
    border: none;
    border-radius: var(--radius-xs);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    opacity: 0;
    flex-shrink: 0;
  }

  .new-chat-btn:hover,
  .new-chat-btn:focus,
  .new-chat-btn:focus-visible {
    color: var(--text);
    background: transparent;
    outline: none;
  }

  .chats-panel {
    display: grid;
    grid-template-rows: 0fr;
    opacity: 0;
    pointer-events: none;
    transition:
      grid-template-rows var(--dur-expand) var(--ease-out),
      opacity var(--dur-expand) var(--ease-out);
  }

  .chats-panel.open {
    grid-template-rows: 1fr;
    opacity: 1;
    pointer-events: auto;
  }

  .chats {
    list-style: none;
    margin: 0 0 0.15rem;
    padding: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
    overflow: hidden;
  }

  .chats > li {
    width: 100%;
  }

  .chat-row {
    position: relative;
    display: flex;
    align-items: center;
    width: 100%;
    border-radius: var(--radius-feedback);
  }

  .chat-row:hover,
  .chat-row.active {
    background: var(--chrome-action-hover);
  }

  .chat-row.active {
    background: var(--selection-bg);
  }

  /* Full-width highlight; indent chats under workspace label */
  .chat {
    flex: 1;
    min-width: 0;
    padding: 0 0.4rem 0 calc(0.35rem + 16px + 0.4rem);
    background: transparent;
  }

  .chat:hover,
  .chat.active {
    background: transparent;
  }

  .chat-row:hover .meta {
    opacity: 0;
  }

  .chat-row:hover .chat-del {
    opacity: 1;
  }

  .chat-del {
    position: absolute;
    right: 0.25rem;
    top: 50%;
    transform: translateY(-50%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    min-width: 20px;
    min-height: 20px;
    padding: 0;
    border: none;
    border-radius: var(--radius-xs);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    opacity: 0;
    flex-shrink: 0;
  }

  .chat-del:hover,
  .chat-del:focus,
  .chat-del:focus-visible {
    color: var(--text);
    background: transparent;
    outline: none;
  }

  .empty-chats {
    padding: 0.2rem 0.4rem 0.35rem calc(16px + 0.4rem + 0.2rem);
    font: inherit;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .rename-input {
    flex: 1;
    min-width: 0;
    height: 22px;
    margin: 0;
    padding: 0 0.35rem;
    border: 1px solid var(--border-active);
    border-radius: var(--radius-xs);
    background: var(--bg-elevated);
    color: var(--text);
    font: inherit;
    font-size: var(--text-base);
  }

  .rename-input:focus {
    outline: none;
  }

  .menu {
    position: fixed;
    z-index: 1400;
    min-width: 10.5rem;
    padding: 0.3rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    background: var(--bg-elevated);
    box-shadow: none;
    -webkit-app-region: no-drag;
    app-region: no-drag;
    pointer-events: auto;
    animation: menu-in var(--dur-fast) var(--ease-out) both;
  }

  .menu button {
    display: block;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: var(--text-base);
    font-weight: inherit;
    padding: 0.35rem 0.5rem;
    border-radius: var(--radius-feedback);
    cursor: pointer;
    transition: background var(--dur-control) var(--ease-out);
  }

  .menu button:hover,
  .menu button:focus-visible {
    background: var(--chrome-action-hover);
    outline: none;
  }

  .menu button.danger {
    color: var(--danger, #c44);
  }

  .menu button.danger:hover,
  .menu button.danger:focus-visible {
    background: color-mix(in srgb, var(--danger, #c44) 12%, transparent);
  }

  @keyframes menu-in {
    from {
      opacity: 0;
      transform: translateY(-4px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @keyframes pin-pop {
    0% {
      transform: scale(0.7) rotate(-18deg);
      opacity: 0.4;
    }
    55% {
      transform: scale(1.2) rotate(8deg);
      opacity: 1;
    }
    100% {
      transform: scale(1) rotate(0deg);
      opacity: 1;
    }
  }

  @keyframes pin-row-flash {
    0% {
      background: transparent;
    }
    35% {
      background: color-mix(in srgb, var(--accent-live) 14%, transparent);
    }
    100% {
      background: transparent;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    li.group,
    li.pin-flash,
    .menu,
    .pin-mark.pop,
    .workspace.pin-pop,
    .workspace-lead .lead-mark,
    .workspace-lead .folder-state,
    .chats-panel {
      animation: none;
      transition: none;
      transform: none;
    }

    .workspace-lead .lead-mark.chevron.open {
      transform: none;
    }

    .chats-panel.open {
      opacity: 1;
      grid-template-rows: 1fr;
    }

    .chats-panel:not(.open) {
      display: none;
    }
  }
</style>
