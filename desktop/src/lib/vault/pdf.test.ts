import { describe, expect, it } from "vitest";
import { isPdfPath } from "./pdf";

describe("pdf", () => {
  it("detects pdf paths", () => {
    expect(isPdfPath("/vault/Lec03.pdf")).toBe(true);
    expect(isPdfPath("/vault/note.md")).toBe(false);
  });
});