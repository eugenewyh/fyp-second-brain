import { afterEach, describe, expect, it, vi } from "vitest";
import {
  loadThemePreference,
  loadPalettePreference,
  resolveEffectiveTheme,
  saveThemePreference,
  savePalettePreference,
  THEME_DEFAULT,
  PALETTE_DEFAULT,
  PALETTE_STORAGE_KEY,
  THEME_STORAGE_KEY,
  isPaletteId,
} from "./theme-prefs";

describe("theme-prefs", () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("defaults to system when storage is empty", () => {
    expect(loadThemePreference()).toBe(THEME_DEFAULT);
    expect(THEME_DEFAULT).toBe("system");
  });

  it("round-trips preference through localStorage", () => {
    saveThemePreference("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(loadThemePreference()).toBe("dark");

    saveThemePreference("light");
    expect(loadThemePreference()).toBe("light");
  });

  it("falls back to system for invalid stored values", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "neon");
    expect(loadThemePreference()).toBe("system");
  });

  it("resolves system preference from matchMedia", () => {
    vi.spyOn(window, "matchMedia").mockImplementation((query: string) => ({
      matches: query.includes("dark"),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    expect(resolveEffectiveTheme("system")).toBe("dark");
    expect(resolveEffectiveTheme("light")).toBe("light");
    expect(resolveEffectiveTheme("dark")).toBe("dark");
  });

  it("resolves system to light when OS prefers light", () => {
    vi.spyOn(window, "matchMedia").mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    expect(resolveEffectiveTheme("system")).toBe("light");
  });

  it("defaults palette to nous when storage is empty", () => {
    expect(loadPalettePreference()).toBe(PALETTE_DEFAULT);
    expect(PALETTE_DEFAULT).toBe("nous");
  });

  it("round-trips palette through localStorage", () => {
    savePalettePreference("ember");
    expect(localStorage.getItem(PALETTE_STORAGE_KEY)).toBe("ember");
    expect(loadPalettePreference()).toBe("ember");
  });

  it("falls back to nous for invalid palette values", () => {
    localStorage.setItem(PALETTE_STORAGE_KEY, "cyberpunk");
    expect(loadPalettePreference()).toBe("nous");
    expect(isPaletteId("cyberpunk")).toBe(false);
    expect(isPaletteId("mono")).toBe(true);
  });
});
