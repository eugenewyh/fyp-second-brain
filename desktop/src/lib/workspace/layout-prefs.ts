/** Persisted shell pane widths (sidebar + document peek). */

const SIDEBAR_KEY = "second-brain-sidebar-width";
const PEEK_KEY = "second-brain-peek-width";

export const SIDEBAR_WIDTH_DEFAULT = 260;
export const SIDEBAR_WIDTH_MIN = 180;
export const SIDEBAR_WIDTH_MAX = 420;

export const PEEK_WIDTH_DEFAULT = 480;
export const PEEK_WIDTH_MIN = 280;
export const PEEK_WIDTH_MAX = 900;

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

function loadWidth(key: string, fallback: number, min: number, max: number): number {
  if (typeof localStorage === "undefined") return fallback;
  const raw = localStorage.getItem(key);
  const n = raw ? Number(raw) : fallback;
  return Number.isFinite(n) ? clamp(n, min, max) : fallback;
}

function saveWidth(key: string, width: number, min: number, max: number): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(key, String(clamp(width, min, max)));
}

export function loadSidebarWidth(): number {
  return loadWidth(SIDEBAR_KEY, SIDEBAR_WIDTH_DEFAULT, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX);
}

export function saveSidebarWidth(width: number): void {
  saveWidth(SIDEBAR_KEY, width, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX);
}

export function clampSidebarWidth(width: number): number {
  return clamp(width, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX);
}

export function loadPeekWidth(): number {
  return loadWidth(PEEK_KEY, PEEK_WIDTH_DEFAULT, PEEK_WIDTH_MIN, PEEK_WIDTH_MAX);
}

export function savePeekWidth(width: number): void {
  saveWidth(PEEK_KEY, width, PEEK_WIDTH_MIN, PEEK_WIDTH_MAX);
}

export function clampPeekWidth(width: number): number {
  return clamp(width, PEEK_WIDTH_MIN, PEEK_WIDTH_MAX);
}
