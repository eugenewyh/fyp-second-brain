export type ResizeSide = "left" | "right";

export const DEFAULT_LEFT_WIDTH = 260;
export const DEFAULT_RIGHT_WIDTH = 300;
export const MIN_PANE_WIDTH = 180;
export const MAX_PANE_WIDTH = 520;
export const MIN_CENTER_WIDTH = 200;
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

/** Keep side panes within bounds so the center pane never shrinks below minCenter. */
export function constrainPaneWidths(
  leftWidth: number,
  rightWidth: number,
  containerWidth: number,
  minCenter = MIN_CENTER_WIDTH,
  minPane = MIN_PANE_WIDTH,
  maxPane = MAX_PANE_WIDTH,
  splitter = SPLITTER_WIDTH,
): { leftWidth: number; rightWidth: number } {
  const splittersTotal = splitter * 2;
  const maxSides = Math.max(minPane * 2, containerWidth - splittersTotal - minCenter);

  let left = clampWidth(leftWidth, minPane, maxPane);
  let right = clampWidth(rightWidth, minPane, maxPane);

  while (left + right > maxSides) {
    if (left >= right && left > minPane) {
      left -= 1;
    } else if (right > minPane) {
      right -= 1;
    } else if (left > minPane) {
      left -= 1;
    } else {
      break;
    }
  }

  return { leftWidth: left, rightWidth: right };
}