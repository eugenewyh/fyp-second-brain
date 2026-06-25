import {
  clampWidth,
  LAYOUT_DEFAULTS,
  LAYOUT_LIMITS,
  loadLayout,
  saveLayout,
  type LayoutState,
} from "$lib/workspace/resize";

class WorkspaceStore {
  leftWidth = $state(LAYOUT_DEFAULTS.leftWidth);
  rightWidth = $state(LAYOUT_DEFAULTS.rightWidth);
  leftCollapsed = $state(LAYOUT_DEFAULTS.leftCollapsed);
  rightCollapsed = $state(LAYOUT_DEFAULTS.rightCollapsed);
  activeNotePath = $state<string | null>(null);
  selectedText = $state("");
  commandPaletteOpen = $state(false);
  vaultSearchQuery = $state("");
  vaultSearchMode = $state<"fuzzy" | "semantic">("fuzzy");
  vaultRefreshNonce = $state(0);
  inspectorTab = $state<"chat" | "agent" | "backlinks" | "sources">("chat");
  vaultRoot = $state<string | null>(null);
  recentNotePaths = $state<string[]>(loadRecentNotePaths());
  pdfJumpPage = $state<number | null>(null);
  watcherStatus = $state<"idle" | "ingesting" | string>("idle");

  init() {
    const saved = loadLayout();
    this.leftWidth = saved.leftWidth;
    this.rightWidth = saved.rightWidth;
    this.leftCollapsed = saved.leftCollapsed;
    this.rightCollapsed = saved.rightCollapsed;
    this.recentNotePaths = loadRecentNotePaths();
  }

  persist() {
    saveLayout(this.snapshot());
  }

  snapshot(): LayoutState {
    return {
      leftWidth: this.leftWidth,
      rightWidth: this.rightWidth,
      leftCollapsed: this.leftCollapsed,
      rightCollapsed: this.rightCollapsed,
    };
  }

  toggleLeft() {
    this.leftCollapsed = !this.leftCollapsed;
    this.persist();
  }

  toggleRight() {
    this.rightCollapsed = !this.rightCollapsed;
    this.persist();
  }

  setLeftWidth(width: number) {
    this.leftWidth = clampWidth(width, LAYOUT_LIMITS.left.min, LAYOUT_LIMITS.left.max);
    this.persist();
  }

  setRightWidth(width: number) {
    this.rightWidth = clampWidth(width, LAYOUT_LIMITS.right.min, LAYOUT_LIMITS.right.max);
    this.persist();
  }

  setActiveNote(path: string | null) {
    this.activeNotePath = path;
    if (path) {
      this.recentNotePaths = [path, ...this.recentNotePaths.filter((p) => p !== path)].slice(0, 8);
      saveRecentNotePaths(this.recentNotePaths);
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
}

const RECENT_STORAGE_KEY = "second-brain-recent-notes";

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

export const workspace = new WorkspaceStore();