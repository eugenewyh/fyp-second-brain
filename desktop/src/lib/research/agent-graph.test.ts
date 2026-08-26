import { describe, expect, it } from "vitest";
import {
  emptyAgentStatuses,
  statusesFromCompletedSteps,
  STEP_TO_NODE,
} from "./agent-graph";

describe("agent-graph", () => {
  it("maps steps to nodes", () => {
    expect(STEP_TO_NODE.planning).toBe("planner");
    expect(STEP_TO_NODE.reviewing).toBe("verifier");
  });

  it("builds statuses from completed steps", () => {
    const s = statusesFromCompletedSteps(["planning", "searching"], "analyzing");
    expect(s.planner).toBe("done");
    expect(s.retriever).toBe("done");
    expect(s.analyst).toBe("running");
    expect(s.verifier).toBe("pending");
  });

  it("empty statuses are all pending", () => {
    const s = emptyAgentStatuses();
    expect(Object.values(s).every((v) => v === "pending")).toBe(true);
  });
});
