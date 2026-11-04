import { describe, expect, it } from "vitest";
import { memorySearchErrorCopy } from "./memory-search-copy";

describe("memorySearchErrorCopy", () => {
  it("maps WebKit Load failed to a clear retry hint", () => {
    expect(memorySearchErrorCopy("Load failed")).toMatch(/Could not reach the AI service/);
  });

  it("maps missing onnx models to a download hint", () => {
    expect(
      memorySearchErrorCopy(
        "[ONNXRuntimeError] : 3 : NO_SUCHFILE : Load model from /tmp/model_optimized.onnx failed",
      ),
    ).toMatch(/incomplete/i);
  });

  it("keeps short unknown errors", () => {
    expect(memorySearchErrorCopy("Chroma is locked")).toBe("Chroma is locked");
  });
});
