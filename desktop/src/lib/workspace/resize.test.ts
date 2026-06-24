import { describe, expect, it } from "vitest";
import {
  applyResize,
  clampWidth,
  constrainPaneWidths,
  DEFAULT_LEFT_WIDTH,
  DEFAULT_RIGHT_WIDTH,
  MAX_PANE_WIDTH,
  MIN_CENTER_WIDTH,
  MIN_PANE_WIDTH,
  SPLITTER_WIDTH,
} from "./resize";

describe("clampWidth", () => {
  it("clamps below minimum", () => {
    expect(clampWidth(50, 180, 520)).toBe(180);
  });

  it("clamps above maximum", () => {
    expect(clampWidth(600, 180, 520)).toBe(520);
  });

  it("returns value within range unchanged", () => {
    expect(clampWidth(300, 180, 520)).toBe(300);
  });
});

describe("applyResize", () => {
  it("widens left pane on positive drag", () => {
    expect(applyResize(260, 40, "left")).toBe(300);
  });

  it("narrows right pane on positive drag", () => {
    expect(applyResize(300, 50, "right")).toBe(250);
  });

  it("respects minimum width", () => {
    expect(applyResize(200, -50, "left")).toBe(180);
  });
});

describe("constrainPaneWidths", () => {
  it("shrinks side panes when both are maxed and center would be too narrow", () => {
    const { leftWidth, rightWidth } = constrainPaneWidths(520, 520, 900);
    expect(leftWidth + rightWidth + SPLITTER_WIDTH * 2 + MIN_CENTER_WIDTH).toBeLessThanOrEqual(900);
    expect(900 - leftWidth - rightWidth - SPLITTER_WIDTH * 2).toBeGreaterThanOrEqual(MIN_CENTER_WIDTH);
  });

  it("leaves widths unchanged when container is wide enough", () => {
    const result = constrainPaneWidths(DEFAULT_LEFT_WIDTH, DEFAULT_RIGHT_WIDTH, 1400);
    expect(result.leftWidth).toBe(DEFAULT_LEFT_WIDTH);
    expect(result.rightWidth).toBe(DEFAULT_RIGHT_WIDTH);
  });

  it("never goes below min pane width", () => {
    const { leftWidth, rightWidth } = constrainPaneWidths(MAX_PANE_WIDTH, MAX_PANE_WIDTH, 500);
    expect(leftWidth).toBeGreaterThanOrEqual(MIN_PANE_WIDTH);
    expect(rightWidth).toBeGreaterThanOrEqual(MIN_PANE_WIDTH);
  });
});