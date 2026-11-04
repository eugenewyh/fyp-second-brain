import { app } from "$lib/stores/app.svelte";
import { workspace } from "$lib/stores/workspace.svelte";

import { setThemePreference } from "$lib/theme/init-theme";

export type CommandCategory = "navigation" | "vault" | "preferences";

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
      label: "Open Memory",
      category: "navigation",
      run: () => app.openMemory(),
    },
    {
      id: "memory",
      label: "Open Memory graph",
      category: "navigation",
      shortcut: "⌘G",
      run: () => app.openMemory(),
    },
    {
      id: "library",
      label: "Open library",
      category: "navigation",
      shortcut: "⌘L",
      run: () => workspace.openLibrary(),
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
