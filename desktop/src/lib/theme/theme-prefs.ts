export type ThemePreference = "light" | "dark" | "system";
export type EffectiveTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "nous-theme-preference";
export const PALETTE_STORAGE_KEY = "nous-theme-palette";
export const THEME_DEFAULT: ThemePreference = "system";
export const PALETTE_DEFAULT = "nous" as const;

export type PaletteId = "nous" | "ember" | "mono";

export function isPaletteId(value: string | null | undefined): value is PaletteId {
  return value === "nous" || value === "ember" || value === "mono";
}

export function isThemePreference(value: string | null | undefined): value is ThemePreference {
  return value === "light" || value === "dark" || value === "system";
}

export function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function resolveEffectiveTheme(pref: ThemePreference): EffectiveTheme {
  if (pref === "system") return systemPrefersDark() ? "dark" : "light";
  return pref;
}

export function loadThemePreference(): ThemePreference {
  if (typeof localStorage === "undefined") return THEME_DEFAULT;
  const raw = localStorage.getItem(THEME_STORAGE_KEY);
  return isThemePreference(raw) ? raw : THEME_DEFAULT;
}

export function saveThemePreference(pref: ThemePreference): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(THEME_STORAGE_KEY, pref);
}

export function loadPalettePreference(): PaletteId {
  if (typeof localStorage === "undefined") return PALETTE_DEFAULT;
  const raw = localStorage.getItem(PALETTE_STORAGE_KEY);
  return isPaletteId(raw) ? raw : PALETTE_DEFAULT;
}

export function savePalettePreference(palette: PaletteId): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(PALETTE_STORAGE_KEY, palette);
}

export function themePreferenceLabel(pref: ThemePreference): string {
  if (pref === "system") return "System";
  if (pref === "dark") return "Dark";
  return "Light";
}

export function effectiveThemeDescription(pref: ThemePreference, effective: EffectiveTheme): string {
  if (pref === "system") {
    return `Using ${effective} (from system)`;
  }
  return `Using ${effective}`;
}
