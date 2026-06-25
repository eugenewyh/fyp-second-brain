import { connection } from "$lib/stores/connection.svelte";
import { research } from "$lib/stores/research.svelte";
import { tabs } from "$lib/stores/tabs.svelte";
import { workspace } from "$lib/stores/workspace.svelte";

export interface CommandAction {
  id: string;
  label: string;
  shortcut?: string;
  run: () => void | Promise<void>;
}

export function getCommands(): CommandAction[] {
  return [
    {
      id: "research",
      label: "Run Research",
      shortcut: "Research tab",
      run: () => {
        tabs.openResearchTab();
      },
    },
    {
      id: "query",
      label: "Quick Query",
      run: () => {
        tabs.openQueryTab();
      },
    },
    {
      id: "ingest",
      label: "Ingest Documents",
      run: () => {
        tabs.openIngestTab();
      },
    },
    {
      id: "settings",
      label: "Open Settings",
      run: () => {
        tabs.openSettingsTab();
      },
    },
    {
      id: "toggle-left",
      label: "Toggle Vault Sidebar",
      run: () => workspace.toggleLeft(),
    },
    {
      id: "toggle-right",
      label: "Toggle Inspector Panel",
      run: () => workspace.toggleRight(),
    },
    {
      id: "focus-vault",
      label: "Focus Vault Search",
      run: () => {
        const el = document.querySelector<HTMLInputElement>("[data-vault-search]");
        el?.focus();
      },
    },
    {
      id: "retry-connection",
      label: "Retry Sidecar Connection",
      run: () => connection.connect(),
    },
    {
      id: "research-deeply",
      label: "Research This Deeply",
      run: () => {
        const q = workspace.selectedText.trim() || workspace.activeNotePath?.split("/").pop() || "";
        if (q) research.runResearch(q);
      },
    },
  ];
}