export type TabType = "research" | "note" | "query" | "ingest" | "settings";

export interface WorkspaceTab {
  id: string;
  type: TabType;
  label: string;
  path?: string;
}

let nextId = 2;

class TabsStore {
  tabs = $state<WorkspaceTab[]>([{ id: "research-1", type: "research", label: "Research" }]);
  activeTabId = $state("research-1");

  get activeTab(): WorkspaceTab | undefined {
    return this.tabs.find((t) => t.id === this.activeTabId);
  }

  activate(id: string) {
    if (this.tabs.some((t) => t.id === id)) {
      this.activeTabId = id;
    }
  }

  openTab(tab: Omit<WorkspaceTab, "id"> & { id?: string }) {
    const existing = tab.path
      ? this.tabs.find((t) => t.type === "note" && t.path === tab.path)
      : this.tabs.find((t) => t.type === tab.type && !tab.path);
    if (existing) {
      this.activeTabId = existing.id;
      return existing.id;
    }
    const id = tab.id ?? `${tab.type}-${nextId++}`;
    this.tabs = [...this.tabs, { ...tab, id }];
    this.activeTabId = id;
    return id;
  }

  closeTab(id: string) {
    if (this.tabs.length <= 1) return;
    const idx = this.tabs.findIndex((t) => t.id === id);
    if (idx === -1) return;
    this.tabs = this.tabs.filter((t) => t.id !== id);
    if (this.activeTabId === id) {
      const next = this.tabs[Math.max(0, idx - 1)];
      this.activeTabId = next.id;
    }
  }

  openResearchTab() {
    return this.openTab({ type: "research", label: "Research" });
  }

  openQueryTab() {
    return this.openTab({ type: "query", label: "Quick Query" });
  }

  openSettingsTab() {
    return this.openTab({ type: "settings", label: "Settings" });
  }

  openIngestTab() {
    return this.openTab({ type: "ingest", label: "Ingest" });
  }

  openNoteTab(path: string, label?: string) {
    const name = label ?? path.split("/").pop() ?? "Note";
    return this.openTab({ type: "note", label: name, path });
  }
}

export const tabs = new TabsStore();