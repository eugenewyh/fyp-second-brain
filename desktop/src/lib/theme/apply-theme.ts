import { setTheme as setTauriTheme } from "@tauri-apps/api/app";
import type { EffectiveTheme, ThemePreference } from "./theme-prefs";

export const THEME_CHANGE_EVENT = "nous-theme-change";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

function updateColorSchemeMeta(theme: EffectiveTheme): void {
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta) meta.setAttribute("content", theme);
}

export function applyEffectiveTheme(theme: EffectiveTheme): void {
  if (typeof document === "undefined") return;

  if (theme === "dark") {
    document.documentElement.dataset.theme = "dark";
  } else {
    delete document.documentElement.dataset.theme;
  }

  updateColorSchemeMeta(theme);
  window.dispatchEvent(new CustomEvent(THEME_CHANGE_EVENT, { detail: { theme } }));
}

export async function syncNativeTheme(
  pref: ThemePreference,
  effective: EffectiveTheme,
): Promise<void> {
  if (!isTauri()) return;
  try {
    await setTauriTheme(pref === "system" ? null : effective);
  } catch {
    // Web preview or Tauri unavailable — ignore.
  }
}
