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
  recentNotePaths = $state<string[]>([]);

  init() {
    const saved = loadLayout();
    this.leftWidth = saved.leftWidth;
    this.rightWidth = saved.rightWidth;
    this.leftCollapsed = saved.leftCollapsed;
    this.rightCollapsed = saved.rightCollapsed;
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

export const workspace = new WorkspaceStore();