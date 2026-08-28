import { describe, expect, it } from "vitest";
import { formatWorkedDuration } from "./elapsed";

describe("formatWorkedDuration", () => {
  it("formats seconds only", () => {
    expect(formatWorkedDuration(0)).toBe("0s");
    expect(formatWorkedDuration(45000)).toBe("45s");
  });

  it("formats minutes and seconds", () => {
    expect(formatWorkedDuration(135000)).toBe("2m 15s");
    expect(formatWorkedDuration(120000)).toBe("2m");
  });

  it("formats hours", () => {
    expect(formatWorkedDuration(339000)).toBe("5m 39s");
    expect(formatWorkedDuration(3600000)).toBe("1h");
    expect(formatWorkedDuration(3900000)).toBe("1h 5m");
  });
});
