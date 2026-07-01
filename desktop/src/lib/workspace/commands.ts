import { connection } from "$lib/stores/connection.svelte";
import { research } from "$lib/stores/research.svelte";
import { tabs } from "$lib/stores/tabs.svelte";
import { workspace } from "$lib/stores/workspace.svelte";

export type CommandCategory = "navigation" | "research" | "vault";

export interface CommandAction {
  id: string;
  label: string;
  category: CommandCategory;
  shortcut?: string;
  run: () => void | Promise<void>;
}

export function getCommands(): CommandAction[] {
  return [
    {
      id: "research",
      label: "Run Research",
      category: "research",
      shortcut: "Research tab",
      run: () => {
        tabs.openResearchTab();
      },
    },
    {
      id: "query",
      label: "Quick Query",
      category: "research",
      run: () => {
        tabs.openQueryTab();
      },
    },
    {
      id: "ingest",
      label: "Ingest Documents",
      category: "vault",
      run: () => {
        tabs.openIngestTab();
      },
    },
    {
      id: "settings",
      label: "Open Settings",
      category: "navigation",
      run: () => {
        tabs.openSettingsTab();
      },
    },
    {
      id: "toggle-left",
      label: "Toggle Vault Sidebar",
      category: "navigation",
      run: () => workspace.toggleLeft(),
    },
    {
      id: "toggle-right",
      label: "Toggle Inspector Panel",
      category: "navigation",
      run: () => workspace.toggleRight(),
    },
    {
      id: "focus-vault",
      label: "Focus Vault Search",
      category: "vault",
      run: () => {
        const el = document.querySelector<HTMLInputElement>("[data-vault-search]");
        el?.focus();
      },
    },
    {
      id: "retry-connection",
      label: "Retry Sidecar Connection",
      category: "navigation",
      run: () => connection.connect(),
    },
    {
      id: "research-deeply",
      label: "Research This Deeply",
      category: "research",
      run: () => {
        const q = workspace.selectedText.trim() || workspace.activeNotePath?.split("/").pop() || "";
        if (q) research.runResearch(q);
      },
    },
  ];
}