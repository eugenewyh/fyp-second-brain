import { describe, expect, it } from "vitest";
import { shouldSaveResearchToVault } from "./notes";

describe("shouldSaveResearchToVault", () => {
  it("saves when the server did not opt out", () => {
    expect(shouldSaveResearchToVault({})).toBe(true);
    expect(shouldSaveResearchToVault({ memory_written: true })).toBe(true);
    expect(shouldSaveResearchToVault({ memory_written: null })).toBe(true);
  });

  it("does not save off-topic lookups the server refused to file", () => {
    expect(shouldSaveResearchToVault({ memory_written: false })).toBe(false);
  });
});
