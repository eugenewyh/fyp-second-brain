export type ResizeSide = "left" | "right";

export const DEFAULT_LEFT_WIDTH = 260;
export const DEFAULT_RIGHT_WIDTH = 300;
export const MIN_PANE_WIDTH = 180;
export const MAX_PANE_WIDTH = 520;
export const SPLITTER_WIDTH = 5;

export function clampWidth(width: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, width));
}

/** Compute next pane width after a horizontal drag delta. */
export function applyResize(
  startWidth: number,
  deltaX: number,
  side: ResizeSide,
  min = MIN_PANE_WIDTH,
  max = MAX_PANE_WIDTH,
): number {
  const next = side === "left" ? startWidth + deltaX : startWidth - deltaX;
  return clampWidth(next, min, max);
}