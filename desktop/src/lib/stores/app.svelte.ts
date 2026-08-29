export type AppMode =
  | "agent"
  | "document"
  | "capabilities"
  | "artifacts"
  | "graph"
  | "watch"
  | "memory";
export type DocumentReturn = "agent" | "artifacts" | "graph";
export type AppSheet =
  | "settings"
  | "ingest"
  | "references"
  | "watch"
  | "memory"
  | "capabilities"
  | "artifacts"
  | null;
export type ArtifactsFilter = "all" | "files" | "links" | "digests";

class AppStore {
  mode = $state<AppMode>("graph");
  documentPath = $state<string | null>(null);
  documentLabel = $state<string | null>(null);
  documentReturn = $state<DocumentReturn>("agent");
  /** Remount document viewers when re-opening same path. */
  documentGeneration = $state(0);
  sheet = $state<AppSheet>(null);
  /** Expanded sources for references sheet (optional payload). */
  referencesSources = $state<{ index: number; source?: string; excerpt?: string }[] | null>(null);
  /** New project creation dialog. */
  newProjectOpen = $state(false);
  /** When set, the project dialog edits this folder instead of creating. */
  editingProjectPath = $state<string | null>(null);
  /** Incremented when opening the Watch tab so the list is shown. */
  watchListNonce = $state(0);
  artifactsFilter = $state<ArtifactsFilter>("all");
  /** When set, Memory graph opens filtered to this workspace folder. */
  memoryTopicFilter = $state<string | null>(null);
  /** Preferred Settings tab when opening the sheet. */
  settingsTab = $state<"appearance" | "models" | "account">("appearance");

  openSettings(tab: "appearance" | "models" | "account" = "appearance") {
    this.settingsTab = tab;
    this.sheet = "settings";
  }

  /** Chat Home (legacy `agent` mode still counts). Watch is a separate tab. */
  get isHome(): boolean {
    return this.mode === "graph" || this.mode === "agent";
  }

  get isAgent(): boolean {
    return this.isHome;
  }

  get isWatch(): boolean {
    return this.sheet === "watch" || this.mode === "watch";
  }

  get isMemory(): boolean {
    return this.sheet === "memory" || this.mode === "memory";
  }

  get isDocument(): boolean {
    return this.mode === "document" && !!this.documentPath;
  }

  /** Document open beside chat (Cursor-style), not a full-page swap. */
  get isDocumentPeek(): boolean {
    return !!this.documentPath && this.mode !== "document";
  }

  get isCapabilities(): boolean {
    return this.sheet === "capabilities" || this.mode === "capabilities";
  }

  get isArtifacts(): boolean {
    return this.sheet === "artifacts" || this.mode === "artifacts";
  }

  get isGraph(): boolean {
    return this.isHome;
  }

  openHome() {
    this.mode = "graph";
    this.documentPath = null;
    this.documentLabel = null;
    this.sheet = null;
  }

  openWatch() {
    this.mode = "graph";
    this.sheet = "watch";
    this.watchListNonce += 1;
  }

  openMemory(opts?: { topicPath?: string | null }) {
    this.memoryTopicFilter = opts?.topicPath ?? null;
    this.mode = "graph";
    this.sheet = "memory";
  }

  openGraph() {
    this.mode = "graph";
    this.sheet = null;
  }

  openAgent() {
    this.mode = "graph";
    this.sheet = null;
  }

  openCapabilities() {
    this.mode = "graph";
    this.sheet = "capabilities";
  }

  openArtifacts(opts?: { filter?: ArtifactsFilter }) {
    this.mode = "graph";
    this.sheet = "artifacts";
    this.artifactsFilter = opts?.filter ?? "all";
  }

  openDocument(path: string, opts?: { label?: string; from?: DocumentReturn }) {
    const name = opts?.label ?? path.split(/[\\/]/).pop() ?? "Document";
    const from = opts?.from ?? "agent";
    const same = this.documentPath === path;

    this.documentPath = path;
    this.documentLabel = name;
    this.documentReturn = from;
    this.sheet = null;
    if (same) this.documentGeneration += 1;

    // Artifacts stays a full-page reader with Back. Chat/graph open beside the thread.
    if (from === "artifacts") {
      this.mode = "document";
      return;
    }
    // Memory hosts its own document peek beside the graph.
    if (this.mode === "memory") {
      return;
    }
    if (this.mode !== "graph" && this.mode !== "agent") {
      this.mode = "graph";
    }
  }

  closeDocument() {
    this.documentPath = null;
    this.documentLabel = null;
    if (this.mode === "document") this.mode = "graph";
  }

  backFromDocument() {
    if (this.documentReturn === "artifacts") {
      this.documentPath = null;
      this.documentLabel = null;
      this.openArtifacts({ filter: this.artifactsFilter });
      return;
    }
    this.closeDocument();
  }

  openNewProject() {
    this.editingProjectPath = null;
    this.newProjectOpen = true;
  }

  openEditProject(path: string) {
    this.editingProjectPath = path;
    this.newProjectOpen = true;
  }

  closeNewProject() {
    this.newProjectOpen = false;
    this.editingProjectPath = null;
  }

  handleEscapePanel(panelOpen: boolean, closePanel: () => void): boolean {
    if (this.newProjectOpen) {
      this.closeNewProject();
      return true;
    }
    if (this.sheet) {
      this.closeSheet();
      return true;
    }
    if (this.documentPath) {
      this.backFromDocument();
      return true;
    }
    if (panelOpen) {
      closePanel();
      return true;
    }
    return false;
  }

  openSheet(sheet: Exclude<AppSheet, null>) {
    this.sheet = sheet;
  }

  closeSheet() {
    this.sheet = null;
    this.referencesSources = null;
  }

  openReferences(sources?: { index: number; source?: string; excerpt?: string }[]) {
    this.referencesSources = sources ?? null;
    this.sheet = "references";
  }
}

export const app = new AppStore();
