import { describe, expect, it } from "vitest";
import { applyResize, clampWidth, DEFAULT_LEFT_WIDTH, DEFAULT_RIGHT_WIDTH } from "./resize";

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

  it("uses shipped defaults as starting widths", () => {
    expect(DEFAULT_LEFT_WIDTH).toBe(260);
    expect(DEFAULT_RIGHT_WIDTH).toBe(300);
    expect(applyResize(DEFAULT_LEFT_WIDTH, 20, "left")).toBe(280);
  });
});