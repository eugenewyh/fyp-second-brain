import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("$lib/api", () => ({
  api: {
    research: vi.fn(),
  },
}));

import { api } from "$lib/api";
import { runResearchQuery } from "./run";

describe("runResearchQuery", () => {
  beforeEach(() => {
    vi.mocked(api.research).mockReset();
  });

  it("returns empty state for blank query without calling API", async () => {
    const result = await runResearchQuery("   ");
    expect(result.result).toBeNull();
    expect(result.error).toBe("");
    expect(api.research).not.toHaveBeenCalled();
  });

  it("returns research result from sidecar on success", async () => {
    const mockResult = {
      query: "servlets",
      plan: "plan text",
      retrieval_queries: [],
      retrieval_stats: {},
      retrieval_log: [],
      analysis: "",
      revision_count: 0,
      report: "## Executive Summary\nDone.",
    };
    vi.mocked(api.research).mockResolvedValueOnce(mockResult);

    const result = await runResearchQuery("servlets");
    expect(api.research).toHaveBeenCalledWith("servlets");
    expect(result.result?.report).toContain("Executive Summary");
    expect(result.error).toBe("");
  });

  it("surfaces API errors", async () => {
    vi.mocked(api.research).mockRejectedValueOnce(new Error("Knowledge base is empty"));
    const result = await runResearchQuery("test");
    expect(result.result).toBeNull();
    expect(result.error).toBe("Knowledge base is empty");
  });
});