import { describe, expect, it } from "vitest";
import { formatAuthError } from "./auth-prefs";

describe("formatAuthError", () => {
  it("extracts FastAPI detail from wrapped Cloud Watch errors", () => {
    expect(
      formatAuthError('Cloud Watch HTTP 401: {"detail":"Invalid email or password"}'),
    ).toBe("Invalid email or password");
  });

  it("passes through already-clean messages", () => {
    expect(formatAuthError(new Error("Invalid email or password"))).toBe(
      "Invalid email or password",
    );
  });

  it("uses fallback for empty input", () => {
    expect(formatAuthError("")).toBe("Could not sign in");
  });
});
