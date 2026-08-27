import { describe, expect, it } from "vitest";
import { formatAuthError } from "./auth-prefs";

describe("formatAuthError", () => {
  it("extracts FastAPI detail from wrapped Cloud Watch errors", () => {
    expect(
      formatAuthError('Cloud Watch HTTP 401: {"detail":"Invalid or expired session"}'),
    ).toBe("Invalid or expired session");
  });

  it("passes through already-clean messages", () => {
    expect(formatAuthError(new Error("Invalid or expired session"))).toBe(
      "Invalid or expired session",
    );
  });

  it("uses fallback for empty input", () => {
    expect(formatAuthError("")).toBe("Could not sign in");
  });
});
