import { app } from "$lib/stores/app.svelte";
import { assistant } from "$lib/stores/assistant.svelte";
import { workspace } from "$lib/stores/workspace.svelte";

import { setThemePreference } from "$lib/theme/init-theme";

export type CommandCategory = "navigation" | "research" | "vault" | "preferences";

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
      id: "home",
      label: "Open Home",
      category: "navigation",
      run: () => app.openHome(),
    },
    {
      id: "watch",
      label: "Open Scheduled Research",
      category: "navigation",
      run: () => app.openWatch(),
    },
    {
      id: "memory",
      label: "Open Memory graph",
      category: "navigation",
      shortcut: "⌘G",
      run: () => workspace.toggleMemoryPanel(),
    },
    {
      id: "library",
      label: "Open library",
      category: "navigation",
      shortcut: "⌘L",
      run: () => workspace.openLibrary(),
    },
    {
      id: "research",
      label: "Single-pass research",
      category: "research",
      run: () => {
        assistant.setComposerMode("research");
        app.openHome();
        const q = assistant.input.trim() || workspace.selectedText.trim();
        if (q) void assistant.runResearch(workspace.activeNotePath, q);
      },
    },
    {
      id: "quick-answer",
      label: "Ask library",
      category: "research",
      run: () => {
        assistant.setComposerMode("quick");
        app.openHome();
      },
    },
    {
      id: "run-goal",
      label: "Run agent goal",
      category: "research",
      run: () => {
        assistant.setComposerMode("goal");
        app.openHome();
        const q = assistant.input.trim() || workspace.selectedText.trim();
        if (q) void assistant.runGoal(q);
      },
    },
    {
      id: "remember-topic",
      label: "Remember notes in this topic",
      category: "vault",
      run: () => {
        app.openHome();
        void assistant.rememberTopicNotes();
      },
    },
    {
      id: "edit-workspace",
      label: "Edit workspace",
      category: "vault",
      run: () => {
        const path = workspace.activeTopicPath;
        if (path) app.openEditProject(path);
      },
    },
    {
      id: "ingest",
      label: "Add documents",
      category: "vault",
      run: () => app.openSheet("ingest"),
    },
    {
      id: "settings",
      label: "Open settings",
      category: "navigation",
      run: () => app.openSheet("settings"),
    },
    {
      id: "theme-light",
      label: "Color Theme: Light",
      category: "preferences",
      run: () => setThemePreference("light"),
    },
    {
      id: "theme-dark",
      label: "Color Theme: Dark",
      category: "preferences",
      run: () => setThemePreference("dark"),
    },
    {
      id: "theme-system",
      label: "Color Theme: System",
      category: "preferences",
      run: () => setThemePreference("system"),
    },
  ];
}
