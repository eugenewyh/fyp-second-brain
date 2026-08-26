import { describe, expect, it, vi } from "vitest";
import {
  MAX_CONCURRENT_RESEARCH,
  abortSessionJob,
  beginPendingTurn,
  canStartResearch,
  endPendingTurn,
  finishSessionJob,
  isSessionBusy,
  isSessionTurnLocked,
  researchJobCount,
  startSessionJob,
} from "./session-jobs";

describe("session job map", () => {
  it("marks only the running session busy", () => {
    let jobs = {};
    const a = startSessionJob(jobs, "a", "research");
    if ("error" in a) throw new Error("expected start");
    jobs = a.jobs;
    expect(isSessionBusy(jobs, "a")).toBe(true);
    expect(isSessionBusy(jobs, "b")).toBe(false);
    expect(isSessionBusy(jobs, null)).toBe(false);
  });

  it("starting chat B does not abort chat A's controller", () => {
    let jobs = {};
    const a = startSessionJob(jobs, "a", "research");
    if ("error" in a) throw new Error("expected start A");
    jobs = a.jobs;
    const aborted = vi.fn();
    a.job.abort.signal.addEventListener("abort", aborted);

    const b = startSessionJob(jobs, "b", "quick");
    if ("error" in b) throw new Error("expected start B");
    jobs = b.jobs;

    expect(aborted).not.toHaveBeenCalled();
    expect(a.job.abort.signal.aborted).toBe(false);
    expect(isSessionBusy(jobs, "a")).toBe(true);
    expect(isSessionBusy(jobs, "b")).toBe(true);
  });

  it("allows one in-flight job per session", () => {
    let jobs = {};
    const a = startSessionJob(jobs, "a", "research");
    if ("error" in a) throw new Error("expected start");
    jobs = a.jobs;
    const again = startSessionJob(jobs, "a", "quick");
    expect("error" in again && again.error).toBe("session_busy");
  });

  it("caps concurrent research but not quick or digest", () => {
    let jobs = {};
    for (let i = 0; i < MAX_CONCURRENT_RESEARCH; i++) {
      const started = startSessionJob(jobs, `r${i}`, "research");
      if ("error" in started) throw new Error(`expected research ${i}`);
      jobs = started.jobs;
    }
    expect(researchJobCount(jobs)).toBe(MAX_CONCURRENT_RESEARCH);
    expect(canStartResearch(jobs)).toBe(false);
    const fifth = startSessionJob(jobs, "r5", "research");
    expect("error" in fifth && fifth.error).toBe("research_cap");

    const quick = startSessionJob(jobs, "q1", "quick");
    if ("error" in quick) throw new Error("expected quick");
    jobs = quick.jobs;
    const digest = startSessionJob(jobs, "d1", "digest");
    if ("error" in digest) throw new Error("expected digest");
  });

  it("aborting A does not abort B", () => {
    let jobs = {};
    const a = startSessionJob(jobs, "a", "research");
    const b = startSessionJob("error" in a ? {} : a.jobs, "b", "research");
    if ("error" in a || "error" in b) throw new Error("expected both");
    jobs = b.jobs;
    jobs = abortSessionJob(jobs, "a", { byUser: true });
    expect(a.job.abort.signal.aborted).toBe(true);
    expect(a.job.cancelledByUser).toBe(true);
    expect(b.job.abort.signal.aborted).toBe(false);
  });

  it("finish A does not finish B", () => {
    let jobs = {};
    const a = startSessionJob(jobs, "a", "research");
    if ("error" in a) throw new Error("expected A");
    const b = startSessionJob(a.jobs, "b", "research");
    if ("error" in b) throw new Error("expected B");
    jobs = finishSessionJob(b.jobs, "a", a.job.abort);
    expect(isSessionBusy(jobs, "a")).toBe(false);
    expect(isSessionBusy(jobs, "b")).toBe(true);
    expect(b.job.abort.signal.aborted).toBe(false);
  });

  it("pending turn locks the session before a job starts", () => {
    let pending: Record<string, true> = {};
    const jobs = {};
    const started = beginPendingTurn(pending, jobs, "a");
    if ("error" in started) throw new Error("expected pending");
    pending = started.pending;
    expect(isSessionTurnLocked(jobs, pending, "a")).toBe(true);
    expect(isSessionBusy(jobs, "a")).toBe(false);

    const again = beginPendingTurn(pending, jobs, "a");
    expect("error" in again && again.error).toBe("session_busy");

    // Real job can still start while pending (handoff from route → quick/research)
    const job = startSessionJob(jobs, "a", "quick");
    if ("error" in job) throw new Error("expected job during pending");
    expect(isSessionBusy(job.jobs, "a")).toBe(true);

    pending = endPendingTurn(pending, "a");
    expect(isSessionTurnLocked(job.jobs, pending, "a")).toBe(true);
  });
});
