import { describe, expect, it } from "vitest";
import {
  cleanStatusDetail,
  failureCopy,
  managerStatusLineForAgent,
  outcomeLine,
  readableStatusLines,
  retrievalStatsLine,
  statusLineForAgent,
} from "./status-copy";
import type { ActivityLogEntry } from "./agent-graph";

describe("status-copy", () => {
  it("cleans long and multiline details", () => {
    expect(cleanStatusDetail("short")).toBe("short");
    expect(cleanStatusDetail("line1\nline2")).toBe("line1");
    expect(cleanStatusDetail("a".repeat(200)).length).toBeLessThanOrEqual(140);
  });

  it("builds agent status sentences", () => {
    expect(statusLineForAgent("retriever", "running")).toMatch(/searching/i);
    expect(statusLineForAgent("verifier", "done")).toMatch(/approved/i);
    expect(statusLineForAgent("planner", "done", "approach ready")).toMatch(/Planner/);
  });

  it("uses Manager voice in the transcript, not specialist names", () => {
    expect(managerStatusLineForAgent("retriever", "running")).toMatch(/notes|search/i);
    expect(managerStatusLineForAgent("retriever", "running")).not.toMatch(/Retriever/i);
    expect(managerStatusLineForAgent("verifier", "done")).toMatch(/checked|analysis/i);
    expect(managerStatusLineForAgent("verifier", "done")).not.toMatch(/Verifier/i);
  });

  it("formats retrieval stats without dumping keys", () => {
    expect(retrievalStatsLine({ personal: 3, web: 2 })).toBe(
      "Retriever finished — 3 from library, 2 web",
    );
  });

  it("dedupes readable status lines", () => {
    const log: ActivityLogEntry[] = [
      { id: "1", time: "09:00:00", agent: "Retriever", message: "Running…", tone: "live" },
      { id: "2", time: "09:00:01", agent: "Retriever", message: "Done", tone: "success" },
      { id: "3", time: "09:00:02", agent: "Retriever", message: "Done", tone: "success" },
      { id: "4", time: "09:00:03", agent: "Memory", message: "Updated chat memory · linked to project", tone: "success" },
    ];
    const lines = readableStatusLines(log);
    expect(lines.length).toBeGreaterThanOrEqual(2);
    expect(lines.some((l) => /Sources in|Retriever finished/i.test(l.text))).toBe(true);
    expect(lines.filter((l) => /Sources in|Retriever finished/i.test(l.text)).length).toBe(1);
  });

  it("builds outcome lines", () => {
    expect(
      outcomeLine({ status: "done", confidence: 0.96, savedPath: "/x.md" }),
    ).toMatch(/Report saved/);
    expect(
      outcomeLine({
        status: "done",
        savedPath: "/x.md",
        memoryDetail: "Answered in chat — not filed into this topic",
      }),
    ).toMatch(/not filed/i);
    expect(outcomeLine({ status: "error", error: "timeout" })).toMatch(/failed/i);
  });

  it("formats failed-run copy for retry UI", () => {
    expect(failureCopy("Could not reach the AI service: Connection error.").title).toMatch(
      /couldn.t reach/i,
    );
    expect(failureCopy("Could not reach the AI service: Connection error.").hint).toMatch(/retry/i);
    expect(failureCopy("AI rate limit reached (tokens/minute). Wait.").title).toMatch(/rate limit/i);
    expect(failureCopy("Planner exploded on step 4").title).toMatch(/Planner exploded/);
  });
});
