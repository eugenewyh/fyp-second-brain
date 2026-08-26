export interface LayoutState {
  leftWidth: number;
  rightWidth: number;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
}

const STORAGE_KEY = "sb-workspace-layout";

/** Agent-first defaults: full-width conversation; drawers open on demand. */
export const LAYOUT_DEFAULTS: LayoutState = {
  leftWidth: 280,
  rightWidth: 340,
  leftCollapsed: true,
  rightCollapsed: true,
};

export const LAYOUT_LIMITS = {
  left: { min: 180, max: 400 },
  right: { min: 220, max: 480 },
};

export function loadLayout(): LayoutState {
  if (typeof localStorage === "undefined") return { ...LAYOUT_DEFAULTS };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...LAYOUT_DEFAULTS };
    return { ...LAYOUT_DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...LAYOUT_DEFAULTS };
  }
}

export function saveLayout(state: LayoutState): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function clampWidth(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}