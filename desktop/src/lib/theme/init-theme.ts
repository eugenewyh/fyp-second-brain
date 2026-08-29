import { applyTheme, syncNativeTheme } from "./apply-theme";
import {
  loadPalettePreference,
  loadThemePreference,
  resolveEffectiveTheme,
  savePalettePreference,
  saveThemePreference,
  type EffectiveTheme,
  type PaletteId,
  type ThemePreference,
} from "./theme-prefs";

let preference: ThemePreference = "system";
let palette: PaletteId = "nous";
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
    applyTheme(palette, effective);
    void syncNativeTheme("system", effective);
  };
  systemMedia.addEventListener("change", systemListener);
}

function applyCurrent(): void {
  effective = resolveEffectiveTheme(preference);
  applyTheme(palette, effective);
  void syncNativeTheme(preference, effective);
}

export function getThemePreference(): ThemePreference {
  return preference;
}

export function getPalettePreference(): PaletteId {
  return palette;
}

export function getEffectiveTheme(): EffectiveTheme {
  return effective;
}

export function initTheme(): void {
  preference = loadThemePreference();
  palette = loadPalettePreference();
  bindSystemListener();
  applyCurrent();
}

export function setThemePreference(next: ThemePreference): void {
  preference = next;
  saveThemePreference(next);
  bindSystemListener();
  applyCurrent();
}

export function setPalettePreference(next: PaletteId): void {
  palette = next;
  savePalettePreference(next);
  applyCurrent();
}
