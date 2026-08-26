import { lastChatInWorkspace, pathsMatch } from "$lib/assistant/workspace-chats";
import { app } from "$lib/stores/app.svelte";
import { assistant, isIdleSession } from "$lib/stores/assistant.svelte";
import { workspace } from "$lib/stores/workspace.svelte";
import { isPdfPath } from "$lib/vault/pdf";

export type ViewMode = "agent" | "document";

export type WorkspaceTab =
  | { id: string; kind: "session"; sessionId: string; label: string }
  | { id: string; kind: "document"; path: string; label: string };

const OPEN_TABS_KEY = "sb-open-tabs-v1";

function notePathsMatch(a: string, b: string): boolean {
  if (a === b) return true;
  if (!isPdfPath(a) || !isPdfPath(b)) return false;
  const aBase = a.split(/[\\/]/).pop()?.toLowerCase() ?? "";
  const bBase = b.split(/[\\/]/).pop()?.toLowerCase() ?? "";
  return aBase.length > 0 && aBase === bBase;
}

function tabIdForSession(sessionId: string): string {
  return `session:${sessionId}`;
}

function tabIdForDocument(path: string): string {
  return `doc:${path}`;
}

type OpenTabsPersist = {
  openSessionIds: string[];
  openDocuments: { path: string; label: string }[];
};

class NavigationStore {
  /** Ordered open session tab ids */
  openSessionIds = $state<string[]>([]);
  openDocuments = $state<{ path: string; label: string }[]>([]);
  private hydrated = false;

  constructor() {
    this.hydrate();
  }

  private hydrate(): void {
    if (this.hydrated || typeof sessionStorage === "undefined") return;
    this.hydrated = true;
    try {
      const raw = sessionStorage.getItem(OPEN_TABS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as OpenTabsPersist;
      if (Array.isArray(parsed.openSessionIds)) {
        this.openSessionIds = parsed.openSessionIds;
      }
      if (Array.isArray(parsed.openDocuments)) {
        this.openDocuments = parsed.openDocuments;
      }
    } catch {
      /* ignore */
    }
  }

  private persist(): void {
    if (typeof sessionStorage === "undefined") return;
    try {
      const payload: OpenTabsPersist = {
        openSessionIds: this.openSessionIds,
        openDocuments: this.openDocuments,
      };
      sessionStorage.setItem(OPEN_TABS_KEY, JSON.stringify(payload));
    } catch {
      /* ignore */
    }
  }

  get view(): ViewMode {
    return app.isDocument ? "document" : "agent";
  }

  get documentPath(): string | null {
    return app.documentPath;
  }

  get documentLabel(): string | null {
    return app.documentLabel;
  }

  get tabFocusGeneration(): number {
    return app.documentGeneration;
  }

  get isDocument(): boolean {
    return app.isDocument;
  }

  /** Live tab list derived from open sessions + labels from assistant. */
  get tabs(): WorkspaceTab[] {
    const known = new Set(Object.keys(assistant.sessions));
    const sessionTabs: WorkspaceTab[] = this.openSessionIds
      .filter((id) => known.has(id))
      .map((sessionId) => {
        const s = assistant.sessions[sessionId];
        return {
          id: tabIdForSession(sessionId),
          kind: "session" as const,
          sessionId,
          label: s?.title || "New research",
        };
      });

    const docTabs: WorkspaceTab[] = this.openDocuments.map((d) => ({
      id: tabIdForDocument(d.path),
      kind: "document" as const,
      path: d.path,
      label: d.label,
    }));

    // Active document tab if open but not yet registered
    if (app.isDocument && app.documentPath) {
      const exists = docTabs.some(
        (t) => t.kind === "document" && notePathsMatch(t.path, app.documentPath!),
      );
      if (!exists) {
        docTabs.push({
          id: tabIdForDocument(app.documentPath),
          kind: "document",
          path: app.documentPath,
          label: app.documentLabel ?? app.documentPath.split(/[\\/]/).pop() ?? "Document",
        });
      }
    }

    return [...sessionTabs, ...docTabs];
  }

  get activeTabId(): string {
    if (app.isDocument && app.documentPath) {
      return tabIdForDocument(app.documentPath);
    }
    if (assistant.activeSessionId) return tabIdForSession(assistant.activeSessionId);
    return "agent";
  }

  get activeTab(): WorkspaceTab | undefined {
    return this.tabs.find((t) => t.id === this.activeTabId);
  }

  /** Ensure session appears in open tabs and is active. */
  openSessionTab(sessionId: string): void {
    if (!assistant.sessions[sessionId]) return;
    if (!this.openSessionIds.includes(sessionId)) {
      this.openSessionIds = [...this.openSessionIds, sessionId];
      this.persist();
    }
    assistant.setActiveSession(sessionId);
  }

  /** Create a new research session and open it as a tab (empty landing). */
  newSessionTab(opts?: { projectPath?: string | null }): string {
    // Reuse the active empty "New chat" tab instead of stacking blanks
    const activeId = assistant.activeSessionId;
    if (activeId && assistant.sessions[activeId]) {
      const s = assistant.sessions[activeId];
      if (isIdleSession(s)) {
        if (opts?.projectPath !== undefined) {
          assistant.setSessionProject(opts.projectPath, activeId);
        }
        this.ensureSessionTab(activeId);
        assistant.setActiveSession(activeId);
        assistant.composerFocusNonce += 1;
        app.openAgent();
        return activeId;
      }
    }

    const id = assistant.createSession({
      focus: true,
      projectPath: opts?.projectPath,
    });
    if (!this.openSessionIds.includes(id)) {
      this.openSessionIds = [...this.openSessionIds, id];
      this.persist();
    }
    app.openAgent();
    return id;
  }

  /** Fresh chat in the open channel (or unbound if none). */
  newWorkspaceChat(): string | null {
    const path = workspace.activeTopicPath;
    if (!path) return this.newSessionTab({ projectPath: null });
    const id = assistant.newChannelSession(path, {
      focus: true,
      channelEmpty: workspace.channelEmpty,
    });
    this.ensureSessionTab(id);
    app.openAgent();
    return id;
  }

  /** Switch the window to a folder: open its most recent chat. */
  openWorkspace(path: string): string | null {
    const next = path.trim();
    if (!next) {
      app.openNewProject();
      return null;
    }
    workspace.setActiveTopic(next);
    const id = assistant.ensureChannelSession(next, {
      focus: true,
      channelEmpty: workspace.channelEmpty,
    });
    this.ensureSessionTab(id);
    app.openHome();
    return id;
  }

  /** Open a specific chat (must already belong to a workspace). */
  openSession(sessionId: string): void {
    if (!assistant.sessions[sessionId]) return;
    this.openSessionTab(sessionId);
    app.openHome();
  }

  /** New chat under an explicit workspace folder. */
  newChatInWorkspace(path: string): string | null {
    const next = path.trim();
    if (!next) return this.newWorkspaceChat();
    workspace.setActiveTopic(next);
    const id = assistant.newChannelSession(next, {
      focus: true,
      channelEmpty: workspace.channelEmpty,
    });
    this.ensureSessionTab(id);
    app.openHome();
    return id;
  }

  /** Keep the open transcript in the current workspace after boot/hydrate. */
  ensureWorkspaceView(): void {
    const path = workspace.activeTopicPath;
    if (!path) return;
    const active = assistant.activeSession;
    if (active && pathsMatch(active.projectPath, path)) {
      this.ensureSessionTab(active.id);
      return;
    }
    const existing = Object.values(assistant.sessions)
      .filter((s) => pathsMatch(s.projectPath, path))
      .sort((a, b) => b.updatedAt - a.updatedAt)[0];
    if (existing) {
      this.openSession(existing.id);
      return;
    }
    // Workspace has no chats — stay empty (user can + New chat)
    assistant.clearActiveSession();
    app.openHome();
  }

  /** Sync open tabs after ensure/create — call when ensuring active session has a tab. */
  ensureSessionTab(sessionId: string): void {
    if (!sessionId || !assistant.sessions[sessionId]) return;
    if (!this.openSessionIds.includes(sessionId)) {
      this.openSessionIds = [...this.openSessionIds, sessionId];
      this.persist();
    }
  }

  closeTab(id: string): void {
    if (id.startsWith("session:")) {
      const sessionId = id.slice("session:".length);
      const idx = this.openSessionIds.indexOf(sessionId);
      this.openSessionIds = this.openSessionIds.filter((s) => s !== sessionId);
      this.persist();

      if (assistant.activeSessionId === sessionId) {
        // Prefer neighboring open session tab
        const nextId =
          this.openSessionIds[Math.max(0, idx - 1)] ?? this.openSessionIds[0] ?? null;
        if (nextId) {
          assistant.setActiveSession(nextId);
        } else {
          this.newWorkspaceChat();
        }
      }
      return;
    }

    if (id.startsWith("doc:")) {
      const path = id.slice("doc:".length);
      this.openDocuments = this.openDocuments.filter((d) => !notePathsMatch(d.path, path));
      this.persist();
      if (app.isDocument && app.documentPath && notePathsMatch(app.documentPath, path)) {
        app.openAgent();
      }
    }
  }

  activate(id: string): void {
    if (id.startsWith("session:")) {
      const sessionId = id.slice("session:".length);
      this.openSessionTab(sessionId);
      return;
    }
    if (id.startsWith("doc:")) {
      const path = id.slice("doc:".length);
      const doc = this.openDocuments.find((d) => notePathsMatch(d.path, path));
      app.openDocument(path, { label: doc?.label, from: "agent" });
      return;
    }
    // Legacy home ids
    if (id === "agent" || id === "home-1" || id.startsWith("home")) {
      app.openAgent();
    }
  }

  goHome() {
    app.openAgent();
  }

  openHomeTab() {
    if (assistant.activeSessionId) {
      this.openSessionTab(assistant.activeSessionId);
    } else {
      this.newWorkspaceChat();
    }
    return this.activeTabId;
  }

  openNoteTab(path: string, label?: string) {
    const name = label ?? path.split(/[\\/]/).pop() ?? "Document";
    const existing = this.openDocuments.find((d) => notePathsMatch(d.path, path));
    if (!existing) {
      this.openDocuments = [...this.openDocuments, { path, label: name }];
      this.persist();
    } else if (label && existing.label !== label) {
      this.openDocuments = this.openDocuments.map((d) =>
        notePathsMatch(d.path, path) ? { ...d, label: name } : d,
      );
      this.persist();
    }
    app.openDocument(path, { label: name, from: "agent" });
    return tabIdForDocument(path);
  }

  /** Prune open session ids that were deleted. */
  pruneMissingSessions(): void {
    const known = new Set(Object.keys(assistant.sessions));
    const next = this.openSessionIds.filter((id) => known.has(id));
    if (next.length !== this.openSessionIds.length) {
      this.openSessionIds = next;
      this.persist();
    }
  }

  /** Clear open session tabs (e.g. after wiping history). Document tabs kept. */
  clearSessionTabs(): void {
    this.openSessionIds = [];
    this.persist();
  }
}

export const tabs = new NavigationStore();
