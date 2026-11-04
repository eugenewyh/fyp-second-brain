import { app } from "$lib/stores/app.svelte";
import {
  ensureDefaultProject,
  getVaultRoot,
  listProjectFolders,
  projectPathExists,
  channelIsEmpty,
} from "$lib/vault/load";
import { reconcileWorkspaceBindings } from "$lib/assistant/workspace-chats";
import { rewritePathPrefix } from "$lib/vault/project-edit";

const SYSTEM = new Set(["research", "memory"]);

class WorkspaceStore {
  activeNotePath = $state<string | null>(null);
  selectedText = $state("");
  commandPaletteOpen = $state(false);
  vaultSearchQuery = $state("");
  vaultSearchMode = $state<"fuzzy" | "semantic">("fuzzy");
  vaultRefreshNonce = $state(0);
  inspectorTab = $state<"backlinks" | "sources">("backlinks");
  vaultRoot = $state<string | null>(null);
  /** Active project folder path under the vault (null = none selected). */
  activeTopicPath = $state<string | null>(loadActiveTopic());
  /** True when the active channel has no IDEA, claims, or rememberable notes. */
  channelEmpty = $state(false);
  /** Live project folders from disk (user projects only). */
  projectFolders = $state<{ name: string; path: string }[]>([]);
  /** Pinned workspace folder paths (sidebar sort). */
  pinnedPaths = $state<string[]>(loadPinnedPaths());
  /** Cursor-style right knowledge panel */
  knowledgePanelOpen = $state(loadPanelOpen());
  /** On Memory, Files is opt-in so the persisted panel doesn't crowd the graph. */
  memoryFilesOpen = $state(false);
  recentNotePaths = $state<string[]>(loadRecentNotePaths());
  pdfJumpPage = $state<number | null>(null);
  watcherStatus = $state<"idle" | "ingesting" | string>("idle");

  /** @deprecated Use app.sheet */
  get utilityPanel(): "ingest" | "settings" | null {
    if (app.sheet === "ingest" || app.sheet === "settings") return app.sheet;
    return null;
  }

  init() {
    this.recentNotePaths = loadRecentNotePaths();
    void this.ensureProjects();
  }

  /**
   * Resolve vault root, seed first-run project if needed, sync disk → UI,
   * rebind active topic, and fix orphan sessions.
   */
  async ensureProjects(): Promise<string | null> {
    try {
      this.vaultRoot = this.vaultRoot ?? (await getVaultRoot());
      await ensureDefaultProject(this.vaultRoot);
      await this.syncProjectsFromDisk();
      return this.activeTopicPath;
    } catch {
      return this.activeTopicPath;
    }
  }

  /** Re-read project folders from disk and reconcile active topic + sessions. */
  async syncProjectsFromDisk(): Promise<void> {
    try {
      const root = this.vaultRoot ?? (await getVaultRoot());
      this.vaultRoot = root;
      const all = await listProjectFolders(root);
      this.projectFolders = all.filter((p) => !SYSTEM.has(p.name.toLowerCase()));

      // Drop pins for folders that no longer exist
      const stillPinned = this.pinnedPaths.filter((p) =>
        this.projectFolders.some((f) => pathsEqual(f.path, p)),
      );
      if (stillPinned.length !== this.pinnedPaths.length) {
        this.pinnedPaths = stillPinned;
        savePinnedPaths(stillPinned);
      }

      const folderPaths = this.projectFolders.map((f) => f.path);
      let sessionList: { id: string; projectPath: string | null }[] = [];
      let deleteOrphan: ((id: string) => void) | null = null;
      try {
        const { assistant } = await import("$lib/stores/assistant.svelte");
        sessionList = Object.values(assistant.sessions).map((s) => ({
          id: s.id,
          projectPath: s.projectPath ?? null,
        }));
        deleteOrphan = (id) => assistant.deleteSession(id);
      } catch {
        /* ignore */
      }
      const result = reconcileWorkspaceBindings({
        folderPaths,
        activeTopicPath: this.activeTopicPath,
        sessions: sessionList,
      });
      if (result.nextActiveTopicPath !== this.activeTopicPath) {
        this.setActiveTopic(result.nextActiveTopicPath);
      }
      if (deleteOrphan) {
        for (const id of result.orphanSessionIds) {
          deleteOrphan(id);
        }
      }
      if (folderPaths.length === 0) {
        try {
          const { assistant } = await import("$lib/stores/assistant.svelte");
          const { app } = await import("$lib/stores/app.svelte");
          assistant.clearActiveSession();
          app.openHome();
        } catch {
          /* ignore */
        }
      }

      // Drop recent notes that no longer exist (best-effort)
      if (this.activeNotePath) {
        const noteOk = await projectPathExists(this.activeNotePath);
        // projectPathExists uses exists() on file path too
        if (!noteOk) this.activeNotePath = null;
      }
      await this.refreshChannelEmpty();
    } catch {
      this.projectFolders = [];
    }
  }

  openLibrary() {
    if (!app.isMemory) app.openMemory();
    this.knowledgePanelOpen = true;
    savePanelOpen(true);
  }

  toggleKnowledgePanel() {
    this.knowledgePanelOpen = !this.knowledgePanelOpen;
    savePanelOpen(this.knowledgePanelOpen);
  }

  setKnowledgePanel(open: boolean) {
    this.knowledgePanelOpen = open;
    savePanelOpen(open);
  }

  toggleMemoryPanel() {
    if (!app.isMemory) app.openMemory();
  }

  setMemoryPanel(open: boolean) {
    if (open && !app.isMemory) app.openMemory();
  }

  openContext(_tab?: "backlinks" | "sources") {
    app.openReferences();
  }

  closeLibrary() {
    this.knowledgePanelOpen = false;
    savePanelOpen(false);
  }

  closeContext() {
    if (app.sheet === "references") app.closeSheet();
  }

  setActiveNote(path: string | null) {
    this.activeNotePath = path;
    if (path) {
      this.recentNotePaths = [path, ...this.recentNotePaths.filter((p) => p !== path)].slice(0, 8);
      saveRecentNotePaths(this.recentNotePaths);
    }
  }

  setActiveTopic(path: string | null) {
    this.activeTopicPath = path;
    saveActiveTopic(path);
    void this.refreshChannelEmpty();
  }

  isPinned(path: string | null | undefined): boolean {
    if (!path) return false;
    return this.pinnedPaths.some((p) => pathsEqual(p, path));
  }

  togglePin(path: string): void {
    if (!path) return;
    if (this.isPinned(path)) {
      this.pinnedPaths = this.pinnedPaths.filter((p) => !pathsEqual(p, path));
    } else {
      // Most recently pinned sorts first.
      this.pinnedPaths = [path, ...this.pinnedPaths.filter((p) => !pathsEqual(p, path))];
    }
    savePinnedPaths(this.pinnedPaths);
  }

  unpin(path: string): void {
    if (!path || !this.isPinned(path)) return;
    this.pinnedPaths = this.pinnedPaths.filter((p) => !pathsEqual(p, path));
    savePinnedPaths(this.pinnedPaths);
  }

  async refreshChannelEmpty(): Promise<void> {
    const path = this.activeTopicPath;
    if (!path) {
      this.channelEmpty = false;
      return;
    }
    try {
      this.channelEmpty = await channelIsEmpty(path);
    } catch {
      this.channelEmpty = false;
    }
  }

  rebindTopicPath(from: string, to: string): void {
    if (!from || !to || from === to) return;
    if (this.activeTopicPath) {
      this.setActiveTopic(rewritePathPrefix(this.activeTopicPath, from, to));
    }
    if (this.activeNotePath) {
      this.activeNotePath = rewritePathPrefix(this.activeNotePath, from, to);
    }
    const recent = this.recentNotePaths.map((p) => rewritePathPrefix(p, from, to));
    if (recent.some((p, i) => p !== this.recentNotePaths[i])) {
      this.recentNotePaths = recent;
      saveRecentNotePaths(recent);
    }
    const pinned = this.pinnedPaths.map((p) => rewritePathPrefix(p, from, to));
    if (pinned.some((p, i) => p !== this.pinnedPaths[i])) {
      this.pinnedPaths = pinned;
      savePinnedPaths(pinned);
    }
    if (app.documentPath) {
      const next = rewritePathPrefix(app.documentPath, from, to);
      if (next !== app.documentPath) app.documentPath = next;
    }
  }

  openCommandPalette() {
    this.commandPaletteOpen = true;
  }

  closeCommandPalette() {
    this.commandPaletteOpen = false;
  }

  requestVaultRefresh() {
    this.vaultRefreshNonce += 1;
  }

  openUtilityPanel(panel: "ingest" | "settings") {
    app.openSheet(panel);
  }

  closeUtilityPanel() {
    app.closeSheet();
  }
}

const RECENT_STORAGE_KEY = "second-brain-recent-notes";
const TOPIC_STORAGE_KEY = "second-brain-active-topic";
const PANEL_STORAGE_KEY = "second-brain-knowledge-panel";
const PINNED_STORAGE_KEY = "second-brain-pinned-workspaces";

function pathsEqual(a: string, b: string): boolean {
  const na = a.replace(/[/\\]+$/, "").toLowerCase();
  const nb = b.replace(/[/\\]+$/, "").toLowerCase();
  return na === nb;
}

function loadRecentNotePaths(): string[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((p) => typeof p === "string").slice(0, 8) : [];
  } catch {
    return [];
  }
}

function saveRecentNotePaths(paths: string[]): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(paths));
}

function loadActiveTopic(): string | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem(TOPIC_STORAGE_KEY);
    return raw && raw.length > 0 ? raw : null;
  } catch {
    return null;
  }
}

function saveActiveTopic(path: string | null): void {
  if (typeof localStorage === "undefined") return;
  if (!path) localStorage.removeItem(TOPIC_STORAGE_KEY);
  else localStorage.setItem(TOPIC_STORAGE_KEY, path);
}

function loadPanelOpen(): boolean {
  if (typeof localStorage === "undefined") return false;
  try {
    return localStorage.getItem(PANEL_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function savePanelOpen(open: boolean): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(PANEL_STORAGE_KEY, open ? "1" : "0");
}

function loadPinnedPaths(): string[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(PINNED_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((p) => typeof p === "string") : [];
  } catch {
    return [];
  }
}

function savePinnedPaths(paths: string[]): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(paths));
}

export const workspace = new WorkspaceStore();
