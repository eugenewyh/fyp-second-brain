import { applyEffectiveTheme, syncNativeTheme } from "./apply-theme";
import {
  loadThemePreference,
  resolveEffectiveTheme,
  saveThemePreference,
  type EffectiveTheme,
  type ThemePreference,
} from "./theme-prefs";

let preference: ThemePreference = "system";
let effective: EffectiveTheme = "light";
let systemMedia: MediaQueryList | null = null;
let systemListener: ((event: MediaQueryListEvent) => void) | null = null;

function unbindSystemListener(): void {
  if (systemMedia && systemListener) {
    systemMedia.removeEventListener("change", systemListener);
  }
  systemMedia = null;
  systemListener = null;
}

function bindSystemListener(): void {
  unbindSystemListener();
  if (typeof window === "undefined" || preference !== "system") return;

  systemMedia = window.matchMedia("(prefers-color-scheme: dark)");
  systemListener = () => {
    if (preference !== "system") return;
    effective = resolveEffectiveTheme("system");
    applyEffectiveTheme(effective);
    void syncNativeTheme("system", effective);
  };
  systemMedia.addEventListener("change", systemListener);
}

function applyCurrent(): void {
  effective = resolveEffectiveTheme(preference);
  applyEffectiveTheme(effective);
  void syncNativeTheme(preference, effective);
}

export function getThemePreference(): ThemePreference {
  return preference;
}

export function getEffectiveTheme(): EffectiveTheme {
  return effective;
}

export function initTheme(): void {
  preference = loadThemePreference();
  bindSystemListener();
  applyCurrent();
}

export function setThemePreference(next: ThemePreference): void {
  preference = next;
  saveThemePreference(next);
  bindSystemListener();
  applyCurrent();
}
