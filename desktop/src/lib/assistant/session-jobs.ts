export const MAX_CONCURRENT_RESEARCH = 4;

export const RESEARCH_CAP_MESSAGE =
  "Four research runs are already in progress. Wait for one to finish, then send again.";

export type SessionJobKind = "research" | "quick" | "digest";

export type SessionJob = {
  kind: SessionJobKind;
  abort: AbortController;
  timeout?: ReturnType<typeof setTimeout>;
  turnId?: string;
  cancelledByUser: boolean;
};

export type StartJobError = "session_busy" | "research_cap";

export function researchJobCount(jobs: Record<string, SessionJob>): number {
  return Object.values(jobs).filter((j) => j.kind === "research").length;
}

export function canStartResearch(jobs: Record<string, SessionJob>): boolean {
  return researchJobCount(jobs) < MAX_CONCURRENT_RESEARCH;
}

export function isSessionBusy(
  jobs: Record<string, SessionJob>,
  sessionId: string | null | undefined,
): boolean {
  return !!sessionId && Object.prototype.hasOwnProperty.call(jobs, sessionId);
}

/** True while submit is routing (before a real job starts) or a job is running. */
export function isSessionTurnLocked(
  jobs: Record<string, SessionJob>,
  pending: Record<string, true>,
  sessionId: string | null | undefined,
): boolean {
  return isSessionBusy(jobs, sessionId) || (!!sessionId && !!pending[sessionId]);
}

/**
 * Claim the session for composer submit before the first await (manager route).
 * Does not create a job — beginJob still works while pending is set.
 */
export function beginPendingTurn(
  pending: Record<string, true>,
  jobs: Record<string, SessionJob>,
  sessionId: string,
): { pending: Record<string, true> } | { error: "session_busy" } {
  if (isSessionTurnLocked(jobs, pending, sessionId)) return { error: "session_busy" };
  return { pending: { ...pending, [sessionId]: true } };
}

export function endPendingTurn(
  pending: Record<string, true>,
  sessionId: string,
): Record<string, true> {
  if (!pending[sessionId]) return pending;
  const next = { ...pending };
  delete next[sessionId];
  return next;
}

export function startSessionJob(
  jobs: Record<string, SessionJob>,
  sessionId: string,
  kind: SessionJobKind,
  opts?: { turnId?: string; timeoutMs?: number },
): { jobs: Record<string, SessionJob>; job: SessionJob } | { error: StartJobError } {
  if (isSessionBusy(jobs, sessionId)) return { error: "session_busy" };
  if (kind === "research" && !canStartResearch(jobs)) return { error: "research_cap" };
  const abort = new AbortController();
  const job: SessionJob = {
    kind,
    abort,
    turnId: opts?.turnId,
    cancelledByUser: false,
  };
  if (opts?.timeoutMs && opts.timeoutMs > 0) {
    job.timeout = setTimeout(() => abort.abort(), opts.timeoutMs);
  }
  return { jobs: { ...jobs, [sessionId]: job }, job };
}

export function finishSessionJob(
  jobs: Record<string, SessionJob>,
  sessionId: string,
  abort?: AbortController,
): Record<string, SessionJob> {
  const job = jobs[sessionId];
  if (!job) return jobs;
  if (abort && job.abort !== abort) return jobs;
  if (job.timeout) clearTimeout(job.timeout);
  const next = { ...jobs };
  delete next[sessionId];
  return next;
}

/** Abort that session's controller only. Does not remove the job (caller ends it in finally). */
export function abortSessionJob(
  jobs: Record<string, SessionJob>,
  sessionId: string,
  opts: { byUser: boolean },
): Record<string, SessionJob> {
  const job = jobs[sessionId];
  if (!job) return jobs;
  job.cancelledByUser = opts.byUser;
  if (job.timeout) {
    clearTimeout(job.timeout);
    job.timeout = undefined;
  }
  job.abort.abort();
  return jobs;
}
