import {
  api,
  type ChatContext,
  type ChatMessage,
  type CritiqueHistoryEntry,
  type DigestResult,
  type ResearchResult,
  type ResearchStreamEvent,
  type RetrievalScope,
  type Source,
} from "$lib/api";
import { connection } from "$lib/stores/connection.svelte";
import { app } from "$lib/stores/app.svelte";
import { workspace } from "$lib/stores/workspace.svelte";
import { flattenVaultFiles } from "$lib/vault/flatten";
import { loadVaultTree } from "$lib/vault/load";
import { saveAndIndexResearch, shouldSaveResearchToVault } from "$lib/vault/notes";
import { isRememberableNotePath } from "$lib/vault/rememberable";
import {
  emptyAgentStatuses,
  formatLogTime,
  NODE_TO_STEP,
  statusesFromCompletedSteps,
  type ActivityLogEntry,
  type AgentNodeId,
  type AgentNodeStatus,
} from "$lib/research/agent-graph";
import {
  retrievalStatsLine,
  statusLineForAgent,
} from "$lib/research/status-copy";
import {
  DEFAULT_SESSION_TITLE,
  canApplyLlmSessionTitle,
  isPlaceholderSessionTitle,
  isTruncatedAutoTitle,
  normalizeLlmSessionTitle,
  phraseTitleFromText,
  titleFromSessionTurns,
  truncateSessionTitle,
} from "$lib/stores/session-title";
import { ONBOARD_OPENER } from "$lib/assistant/channel-agents";
import { rewritePathPrefix } from "$lib/vault/project-edit";
import { pathsMatch, folderLabel } from "$lib/assistant/workspace-chats";
import {
  RESEARCH_CAP_MESSAGE,
  abortSessionJob,
  beginPendingTurn,
  endPendingTurn,
  finishSessionJob,
  isSessionBusy,
  isSessionTurnLocked,
  startSessionJob,
  type SessionJob,
  type SessionJobKind,
} from "$lib/assistant/session-jobs";

/** @deprecated Prefer sessions; kept for migration / call-site compatibility. */
export const HOME_THREAD_KEY = "__home__";

/** First line for a ready Memory chat — unused; empty ready chats stay quiet. */
export const MANAGER_OPENER = "Hey. What are you working on?";

const THREAD_STORAGE_KEY_V1 = "sb-agent-thread-v1";
const SESSIONS_STORAGE_KEY = "sb-agent-sessions-v2";

export type ResearchProgressStep =
  | "planning"
  | "searching"
  | "analyzing"
  | "reviewing"
  | "writing";

export const RESEARCH_STEPS: { id: ResearchProgressStep; label: string }[] = [
  { id: "planning", label: "Planner: break down the task" },
  { id: "searching", label: "Retriever: your library + web + arXiv" },
  { id: "analyzing", label: "Analyst: extract insights" },
  { id: "reviewing", label: "Verifier: self-critique loop" },
  { id: "writing", label: "Synthesizer: structured output → memory" },
];

const RESEARCH_TIMEOUT_MS = 30 * 60 * 1000;

export type ComposerAttachment = {
  id: string;
  name: string;
  path?: string;
  text?: string;
};

export type AssistantTurn =
  | { id: string; kind: "user"; content: string }
  | {
      id: string;
      kind: "quick";
      role: "assistant";
      content: string;
      sources: Source[];
      error?: string;
      thinMemory?: boolean;
    }
  | {
      id: string;
      kind: "digest";
      status: "running" | "done" | "error";
      label: string;
      savedPath?: string;
      contentHash?: string;
      idempotent?: boolean;
      claimsCreated?: number;
      claimsRevised?: number;
      claimsDropped?: number;
      linkedSources?: string[];
      summary?: string;
      error?: string;
      retryText?: string;
      retryPaths?: string[];
    }
  | {
      id: string;
      kind: "research";
      query: string;
      status: "awaiting_plan" | "running" | "done" | "error";
      progressStep: ResearchProgressStep;
      progressDetail?: string;
      completedSteps?: ResearchProgressStep[];
      result?: ResearchResult;
      error?: string;
      showAdvanced?: boolean;
      savedPath?: string;
      learningPath?: string;
      indexed?: boolean;
      agentStatuses?: Record<AgentNodeId, AgentNodeStatus>;
      activityLog?: ActivityLogEntry[];
      livePlan?: string;
      liveQueries?: string[];
      liveCritiqueHistory?: CritiqueHistoryEntry[];
      looping?: boolean;
      runId?: string;
      planExpiresAt?: string;
      priorContext?: string;
      retrievalScope?: RetrievalScope;
      /** Extra topic folders for this turn only. Reads union; writes stay bound. */
      alsoProjectPaths?: string[];
      /** studio = single research (+ plan review); goal = multi-pass autonomous */
      runMode?: "studio" | "goal";
      goalPass?: number;
      goalMaxPasses?: number;
      memoryRecalled?: number;
      memoryDetail?: string;
      claimCount?: number;
      confidence?: number;
      goalStatus?: string;
    }
  | { id: string; kind: "manager"; content: string };

export type SessionInterview = {
  clarifyCount: number;
};

export type ChatSession = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: AssistantTurn[];
  /** Vault topic/project path, or null = all knowledge */
  projectPath?: string | null;
  interview?: SessionInterview;
  /** Unsent composer text — keeps an otherwise-empty New chat in the sidebar. */
  draftInput?: string;
  /** Unsent attachments staged in the composer for this chat. */
  draftAttachments?: ComposerAttachment[];
};

/** Blank or opener-only — no Teach / Ask / Research work yet. */
export function isIdleSession(s: { turns: AssistantTurn[] }): boolean {
  return !s.turns.some((t) => t.kind !== "manager");
}

/** Typed (or attached) but not sent — still counts as a kept New chat. */
export function sessionHasDraft(s: {
  draftInput?: string;
  draftAttachments?: ComposerAttachment[];
}): boolean {
  return !!(s.draftInput?.trim() || (s.draftAttachments?.length ?? 0) > 0);
}

/**
 * Drop blank New chats when navigating away.
 * Keep: active chat, busy chat, any with a user message, or any with unsent draft.
 */
export function shouldDiscardIdleSession(
  session: {
    turns: AssistantTurn[];
    draftInput?: string;
    draftAttachments?: ComposerAttachment[];
  },
  opts: { isActive: boolean; isBusy?: boolean },
): boolean {
  if (opts.isActive || opts.isBusy) return false;
  if (!isIdleSession(session)) return false;
  if (sessionHasDraft(session)) return false;
  return true;
}

export type SessionListItem = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turnCount: number;
  /** Vault topic/project path, or null = all knowledge */
  projectPath: string | null;
};

export type RunningJobItem = {
  sessionId: string;
  projectPath: string | null;
  label: string;
  kind: SessionJobKind;
  needsReview: boolean;
};

export type ResearchMissionItem = {
  turnId: string;
  sessionId: string;
  sessionTitle: string;
  query: string;
  status: Extract<AssistantTurn, { kind: "research" }>["status"];
  statusLabel: string;
  updatedAt: number;
  confidence?: number;
  runMode?: "studio" | "goal";
  goalStatus?: string;
  indexed?: boolean;
  savedPath?: string;
};

function newId(): string {
  return crypto.randomUUID();
}

function mapStreamStep(step: string): ResearchProgressStep {
  if (step === "searching_docs" || step === "searching_web" || step === "searching") {
    return "searching";
  }
  if (step === "planning" || step === "analyzing" || step === "reviewing" || step === "writing") {
    return step;
  }
  return "planning";
}

function isAgentNode(node: string): node is AgentNodeId {
  return (
    node === "planner" ||
    node === "retriever" ||
    node === "analyst" ||
    node === "verifier" ||
    node === "synthesizer"
  );
}

function threadToChatMessages(turns: AssistantTurn[]): ChatMessage[] {
  const messages: ChatMessage[] = [];
  for (const turn of turns) {
    if (turn.kind === "user") {
      messages.push({ role: "user", content: turn.content });
    } else if (turn.kind === "manager") {
      messages.push({ role: "assistant", content: turn.content });
    } else if (turn.kind === "quick" && !turn.error) {
      messages.push({ role: "assistant", content: turn.content });
    }
  }
  return messages;
}

function serializeThread(turns: AssistantTurn[]): AssistantTurn[] {
  return turns
    .map((t) => {
      if (t.kind === "research" && t.status === "running") {
        return { ...t, status: "error" as const, error: "Interrupted — run again" };
      }
      if (t.kind === "digest" && t.status === "running") {
        return { ...t, status: "error" as const, error: "Interrupted — remember again" };
      }
      if (t.kind === "research") {
        const { activityLog: _a, ...rest } = t;
        return rest;
      }
      return t;
    })
    .slice(-40);
}

function researchStatusLabel(
  status: Extract<AssistantTurn, { kind: "research" }>["status"],
): string {
  if (status === "awaiting_plan") return "plan";
  if (status === "running") return "running";
  if (status === "error") return "failed";
  return "done";
}

type SessionsPersist = {
  activeSessionId: string | null;
  sessions: ChatSession[];
};

class AssistantStore {
  input = $state("");
  sessions = $state<Record<string, ChatSession>>({});
  activeSessionId = $state<string | null>(null);
  lastSources = $state<Source[]>([]);
  activeResearchTurnId = $state<string | null>(null);
  private jobs = $state<Record<string, SessionJob>>({});
  /** Composer submit claimed this session before manager route / job begin. */
  private pendingTurns = $state<Record<string, true>>({});
  ingestSuggestions = $state<string[]>([]);
  selectedAgentNode = $state<AgentNodeId | null>(null);
  planReviewEnabled = $state(true);
  focusedTurnId = $state<string | null>(null);
  retrievalScope = $state<RetrievalScope>("hybrid");
  composerFocusNonce = $state(0);

  /** Prefill the composer and open Agent (graph “ask this node”). */
  prepareAsk(text: string) {
    this.input = text;
    this.composerFocusNonce += 1;
    app.openAgent();
  }
  /**
   * Agent surface mode:
   * - mission: chat thread (default for research/goal)
   * - report: Elicit-style reading of completed research
   * - ask: library Q&A in the same thread
   */
  viewMode = $state<"mission" | "report" | "ask">("mission");
  /** Optional right details drawer (plan / critique / summary). Default closed. */
  inspectorOpen = $state(false);
  /** Composer segment: goal (autonomous) | research (studio) | quick (library). */
  composerMode = $state<"goal" | "research" | "quick">("quick");
  maxGoalPasses = $state(2);

  async loadHarnessDefaults(): Promise<void> {
    try {
      const d = await api.agentDefaults();
      if (typeof d.max_goal_passes === "number" && Number.isFinite(d.max_goal_passes)) {
        this.maxGoalPasses = Math.max(1, Math.min(4, Math.round(d.max_goal_passes)));
      }
    } catch {
      /* sidecar not ready */
    }
  }

  attachments = $state<ComposerAttachment[]>([]);
  /** Quiet thread status for inferred routing (not a mode tab). */
  routeStatus = $state<"teach" | "explain" | "lookup" | null>(null);
  /**
   * Force next Manager job (Shift+Tab / plus menu). null = Auto.
   * Maps: Ask→answer, Research→research, Teach→file.
   */
  forcedJob = $state<"answer" | "research" | "file" | null>(null);

  cycleForcedJob(): void {
    const order: Array<"answer" | "research" | "file" | null> = [
      null,
      "answer",
      "research",
      "file",
    ];
    const i = order.indexOf(this.forcedJob);
    this.forcedJob = order[(i + 1) % order.length];
  }

  setForcedJob(job: "answer" | "research" | "file" | null): void {
    this.forcedJob = job;
  }

  forcedJobLabel(): string {
    if (this.forcedJob === "answer") return "Ask";
    if (this.forcedJob === "research") return "Research";
    if (this.forcedJob === "file") return "Teach";
    return "Auto";
  }

  cycleRetrievalScope(): void {
    const order: RetrievalScope[] = ["local", "hybrid", "web"];
    const i = order.indexOf(this.retrievalScope);
    this.retrievalScope = order[(i + 1) % order.length];
  }

  setRetrievalScope(scope: RetrievalScope): void {
    this.retrievalScope = scope;
  }

  setComposerMode(mode: "goal" | "research" | "quick"): void {
    this.composerMode = mode;
    if (mode === "quick") {
      this.setRetrievalScope("local");
      this.viewMode = "ask";
    } else {
      this.viewMode = "mission";
      if (mode === "goal") this.planReviewEnabled = false;
    }
  }

  setViewMode(mode: "mission" | "report" | "ask"): void {
    this.viewMode = mode;
    if (mode === "ask") this.composerMode = "quick";
    if (mode === "mission" && this.composerMode === "quick") {
      this.composerMode = "goal";
    }
  }

  openMissionView(turnId?: string, sessionId?: string): void {
    if (turnId) this.focusTurn(turnId, sessionId);
    this.viewMode = "mission";
    this.inspectorOpen = false;
    app.openAgent();
  }

  /** Open the saved report note beside chat. */
  openReportView(turnId?: string, sessionId?: string): void {
    if (turnId) this.focusTurn(turnId, sessionId);
    this.viewMode = "mission";
    this.inspectorOpen = false;
    app.openAgent();
    const turn = this.getMissionTurn();
    const path =
      turn?.savedPath ?? turn?.result?.report_path ?? turn?.result?.saved_path ?? null;
    if (!path) return;
    app.openDocument(path, { label: "Report", from: "agent" });
    workspace.setActiveNote(path);
  }

  closeReportView(): void {
    if (this.viewMode === "report") this.viewMode = "mission";
    app.closeDocument();
  }

  toggleInspector(): void {
    this.inspectorOpen = !this.inspectorOpen;
  }

  private hydrated = false;

  constructor() {
    this.hydrate();
  }

  sessionBusy(id: string | null | undefined): boolean {
    return isSessionBusy(this.jobs, id);
  }

  /** True while routing a submit or running a job — blocks a second send. */
  sessionTurnLocked(id: string | null | undefined): boolean {
    return isSessionTurnLocked(this.jobs, this.pendingTurns, id);
  }

  /**
   * Claim the session before the first await in composer submit.
   * Keeps isLoading true so Enter key-repeat / double-click cannot start a
   * second manager+answer cycle for the same message.
   */
  beginPendingTurn(sessionId: string): boolean {
    const result = beginPendingTurn(this.pendingTurns, this.jobs, sessionId);
    if ("error" in result) return false;
    this.pendingTurns = result.pending;
    return true;
  }

  endPendingTurn(sessionId: string): void {
    this.pendingTurns = endPendingTurn(this.pendingTurns, sessionId);
  }

  sessionBusyForTurn(turnId: string): boolean {
    for (const job of Object.values(this.jobs)) {
      if (job.turnId === turnId) return true;
    }
    const located = this.locateResearchTurn(turnId);
    return located ? this.sessionTurnLocked(located.sessionId) : false;
  }

  get isLoading(): boolean {
    return this.sessionTurnLocked(this.activeSessionId);
  }

  get researchLoading(): boolean {
    return this.jobs[this.activeSessionId ?? ""]?.kind === "research";
  }

  get quickLoading(): boolean {
    return this.jobs[this.activeSessionId ?? ""]?.kind === "quick";
  }

  get digestLoading(): boolean {
    return this.jobs[this.activeSessionId ?? ""]?.kind === "digest";
  }

  get runningJobCount(): number {
    return Object.keys(this.jobs).length;
  }

  listRunningJobs(): RunningJobItem[] {
    const out: RunningJobItem[] = [];
    for (const [sessionId, job] of Object.entries(this.jobs)) {
      const s = this.sessions[sessionId];
      if (!s) continue;
      let label = "";
      let needsReview = false;
      for (const t of s.turns) {
        if (t.kind === "research" && t.status === "awaiting_plan") {
          needsReview = true;
          label = t.query;
          break;
        }
        if (t.kind === "research" && (t.status === "running" || job.turnId === t.id)) {
          label = t.query;
        }
        if (t.kind === "digest" && t.status === "running") {
          label = t.label || "Filing notes";
        }
      }
      if (!label) {
        label =
          job.kind === "quick"
            ? "Answering"
            : job.kind === "digest"
              ? "Filing notes"
              : "Research";
      }
      out.push({
        sessionId,
        projectPath: s.projectPath ?? null,
        label,
        kind: job.kind,
        needsReview,
      });
    }
    return out.sort((a, b) => {
      if (a.needsReview !== b.needsReview) return a.needsReview ? -1 : 1;
      return 0;
    });
  }

  private beginJob(
    sessionId: string,
    kind: SessionJobKind,
    opts?: { turnId?: string; timeoutMs?: number },
  ): SessionJob | { error: "session_busy" | "research_cap" } {
    const result = startSessionJob(this.jobs, sessionId, kind, opts);
    if ("error" in result) return result;
    this.jobs = result.jobs;
    return result.job;
  }

  private endJob(sessionId: string, abort?: AbortController): void {
    this.jobs = finishSessionJob(this.jobs, sessionId, abort);
  }

  cancelSession(id: string): void {
    this.jobs = abortSessionJob(this.jobs, id, { byUser: true });
  }

  get activeSession(): ChatSession | null {
    if (!this.activeSessionId) return null;
    return this.sessions[this.activeSessionId] ?? null;
  }

  /** Active session thread (preferred). */
  getActiveThread(): AssistantTurn[] {
    return this.activeSession?.turns ?? [];
  }

  /** @deprecated Use getActiveThread */
  getHomeThread(): AssistantTurn[] {
    return this.getActiveThread();
  }

  getThread(_notePath: string | null): AssistantTurn[] {
    return this.getActiveThread();
  }

  /** Sidebar + search: chats the user has actually spoken in. */
  listSessions(): SessionListItem[] {
    return Object.values(this.sessions)
      .filter((s) => !isIdleSession(s))
      .map((s) => ({
        id: s.id,
        title: s.title || DEFAULT_SESSION_TITLE,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
        turnCount: s.turns.length,
        projectPath: s.projectPath ?? null,
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  }

  /** Bound channel sessions — blank New chats only while active; drafts stay after leave. */
  listChannelSessions(): SessionListItem[] {
    return Object.values(this.sessions)
      .filter((s) => !!s.projectPath)
      .filter(
        (s) =>
          !isIdleSession(s) || s.id === this.activeSessionId || sessionHasDraft(s),
      )
      .map((s) => ({
        id: s.id,
        title: s.title || DEFAULT_SESSION_TITLE,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
        turnCount: s.turns.length,
        projectPath: s.projectPath ?? null,
      }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  }

  listResearchMissions(): ResearchMissionItem[] {
    const out: ResearchMissionItem[] = [];
    for (const s of Object.values(this.sessions)) {
      for (const t of s.turns) {
        if (t.kind !== "research") continue;
        out.push({
          turnId: t.id,
          sessionId: s.id,
          sessionTitle: s.title || "New research",
          query: t.query,
          status: t.status,
          statusLabel: researchStatusLabel(t.status),
          updatedAt: s.updatedAt,
          confidence: t.confidence ?? t.result?.confidence ?? undefined,
          runMode: t.runMode,
          goalStatus: t.goalStatus ?? t.result?.goal_status ?? undefined,
          indexed: t.indexed,
          savedPath: t.savedPath ?? t.result?.report_path ?? undefined,
        });
      }
    }
    return out.sort((a, b) => b.updatedAt - a.updatedAt);
  }

  /** Active or focused research turn for Mission panel. */
  getMissionTurn(): Extract<AssistantTurn, { kind: "research" }> | null {
    const sid = this.activeSessionId;
    if (!sid) return null;
    const thread = this.getThreadForSession(sid);
    if (this.focusedTurnId) {
      const focused = thread.find(
        (t): t is Extract<AssistantTurn, { kind: "research" }> =>
          t.id === this.focusedTurnId && t.kind === "research",
      );
      if (focused) return focused;
    }
    if (this.activeResearchTurnId) {
      const active = thread.find(
        (t): t is Extract<AssistantTurn, { kind: "research" }> =>
          t.id === this.activeResearchTurnId && t.kind === "research",
      );
      if (active) return active;
    }
    for (let i = thread.length - 1; i >= 0; i--) {
      const t = thread[i];
      if (t.kind === "research") return t;
    }
    return null;
  }

  /** Recent research missions in the active session (compat). */
  recentMissions(): {
    id: string;
    query: string;
    statusLabel: string;
  }[] {
    const out: { id: string; query: string; statusLabel: string }[] = [];
    for (const t of this.getActiveThread()) {
      if (t.kind !== "research") continue;
      out.push({
        id: t.id,
        query: t.query,
        statusLabel: researchStatusLabel(t.status),
      });
    }
    return out.reverse().slice(0, 16);
  }

  ensureActiveSession(): string {
    if (this.activeSessionId && this.sessions[this.activeSessionId]) {
      return this.activeSessionId;
    }
    return this.createSession({
      focus: false,
      projectPath: workspace.activeTopicPath,
    });
  }

  createSession(opts?: {
    focus?: boolean;
    title?: string;
    projectPath?: string | null;
    channelEmpty?: boolean;
  }): string {
    const prev = this.activeSessionId;
    if (prev) this.stashComposerDraft(prev);

    const id = newId();
    const now = Date.now();
    const projectPath = opts?.projectPath !== undefined ? opts.projectPath : null;
    const title = opts?.title?.trim() || DEFAULT_SESSION_TITLE;
    const opener = opts?.channelEmpty ? ONBOARD_OPENER : "";
    const session: ChatSession = {
      id,
      title,
      createdAt: now,
      updatedAt: now,
      turns: opener ? [{ id: newId(), kind: "manager", content: opener }] : [],
      projectPath: projectPath ?? null,
      interview: { clarifyCount: 0 },
      draftInput: "",
      draftAttachments: [],
    };
    this.sessions = { ...this.sessions, [id]: session };
    this.activeSessionId = id;
    this.focusedTurnId = null;
    this.lastSources = [];
    this.selectedAgentNode = null;
    this.input = "";
    this.attachments = [];
    if (projectPath) workspace.setActiveTopic(projectPath);
    this.touchSessionOrder(id);
    // Discard any previous unused New chat now that this one is active.
    this.pruneEmptySessions();
    this.persist();
    if (opts?.focus !== false) {
      app.openAgent();
      app.closeSheet();
      workspace.setKnowledgePanel(false);
      this.composerFocusNonce += 1;
    }
    return id;
  }

  /** Find or create a chat for a channel folder (newest existing, else new). */
  ensureChannelSession(
    path: string,
    opts?: { focus?: boolean; channelEmpty?: boolean },
  ): string {
    const existing = Object.values(this.sessions)
      .filter((s) => pathsMatch(s.projectPath, path))
      .sort((a, b) => b.updatedAt - a.updatedAt)[0];
    if (existing) {
      if (opts?.focus !== false) this.setActiveSession(existing.id);
      else this.persist();
      return existing.id;
    }
    return this.createSession({
      focus: opts?.focus !== false,
      projectPath: path,
      channelEmpty: opts?.channelEmpty,
    });
  }

  /** Always start a fresh chat in this folder (reuse one idle blank if present). */
  newChannelSession(
    path: string,
    opts?: { focus?: boolean; channelEmpty?: boolean },
  ): string {
    const idle = Object.values(this.sessions)
      .filter((s) => pathsMatch(s.projectPath, path) && isIdleSession(s))
      .sort((a, b) => b.updatedAt - a.updatedAt)[0];
    if (idle) {
      if (opts?.focus !== false) this.setActiveSession(idle.id);
      else this.persist();
      return idle.id;
    }
    return this.createSession({
      focus: opts?.focus !== false,
      projectPath: path,
      channelEmpty: opts?.channelEmpty,
    });
  }

  setActiveSession(id: string): void {
    if (!this.sessions[id]) return;
    const prev = this.activeSessionId;
    if (prev && prev !== id) this.stashComposerDraft(prev);
    this.activeSessionId = id;
    this.focusedTurnId = null;
    this.selectedAgentNode = null;
    this.restoreComposerDraft(id);
    // Do not bump updatedAt / sidebar order on select — only on send (patchSession).
    const project = this.sessions[id].projectPath ?? null;
    if (project) workspace.setActiveTopic(project);
    const job = this.jobs[id];
    if (job?.kind === "quick") this.routeStatus = "explain";
    else if (job?.kind === "digest") this.routeStatus = "teach";
    else if (job?.kind === "research") this.routeStatus = "lookup";
    else this.routeStatus = null;
    this.activeResearchTurnId = job?.turnId ?? null;
    // Unused New chats (no message, no draft) disappear when left.
    this.pruneEmptySessions();
    this.persist();
    app.openAgent();
  }

  /** Save unsent composer text/files onto a session before leaving it. */
  private stashComposerDraft(sessionId: string): void {
    const s = this.sessions[sessionId];
    if (!s) return;
    const draftInput = this.input;
    const draftAttachments = this.attachments.map((a) => ({ ...a }));
    const hasDraft = sessionHasDraft({ draftInput, draftAttachments });
    this.sessions = {
      ...this.sessions,
      [sessionId]: {
        ...s,
        draftInput,
        draftAttachments,
        // Only bump recency when there is a real draft — empty stash must not
        // push the previous chat above a freshly created New Chat.
        ...(hasDraft ? { updatedAt: Date.now() } : {}),
      },
    };
  }

  /** Move a chat to the top of the sidebar (strictly newest updatedAt). */
  private touchSessionOrder(sessionId: string): void {
    const s = this.sessions[sessionId];
    if (!s) return;
    const newest = Object.values(this.sessions).reduce(
      (max, x) => Math.max(max, x.updatedAt),
      0,
    );
    const updatedAt = Math.max(Date.now(), newest + 1);
    this.sessions = {
      ...this.sessions,
      [sessionId]: { ...s, updatedAt },
    };
  }

  private restoreComposerDraft(sessionId: string): void {
    const s = this.sessions[sessionId];
    this.input = s?.draftInput ?? "";
    this.attachments = (s?.draftAttachments ?? []).map((a) => ({ ...a }));
  }

  /** Clear unsent draft after a message is sent from this session. */
  private clearComposerDraft(sessionId: string | null | undefined): void {
    if (!sessionId || !this.sessions[sessionId]) return;
    const s = this.sessions[sessionId];
    if (!s.draftInput && !(s.draftAttachments?.length ?? 0)) return;
    this.sessions = {
      ...this.sessions,
      [sessionId]: { ...s, draftInput: "", draftAttachments: [] },
    };
  }

  /** Bind project/topic for the active (or given) session. */
  setSessionProject(projectPath: string | null, sessionId?: string): void {
    const sid = sessionId ?? this.activeSessionId;
    if (!sid || !this.sessions[sid]) return;
    const s = this.sessions[sid];
    this.sessions = {
      ...this.sessions,
      [sid]: { ...s, projectPath, updatedAt: Date.now() },
    };
    if (sid === this.activeSessionId) {
      workspace.setActiveTopic(projectPath);
    }
    this.persist();
  }

  /** Rewrite session project paths after a workspace folder is renamed. Call before syncing disk. */
  rebindProjectPath(from: string, to: string): void {
    if (!from || !to || from === to) return;
    let changed = false;
    const next: Record<string, ChatSession> = {};
    for (const [id, s] of Object.entries(this.sessions)) {
      const projectPath = s.projectPath
        ? rewritePathPrefix(s.projectPath, from, to)
        : s.projectPath;
      let turnsChanged = false;
      const turns = s.turns.map((t) => {
        if (t.kind !== "research") return t;
        const alsoProjectPaths = t.alsoProjectPaths?.map((p) => rewritePathPrefix(p, from, to));
        const savedPath = t.savedPath ? rewritePathPrefix(t.savedPath, from, to) : t.savedPath;
        const learningPath = t.learningPath
          ? rewritePathPrefix(t.learningPath, from, to)
          : t.learningPath;
        const alsoChanged =
          !!alsoProjectPaths &&
          alsoProjectPaths.some((p, i) => p !== t.alsoProjectPaths![i]);
        if (!alsoChanged && savedPath === t.savedPath && learningPath === t.learningPath) {
          return t;
        }
        turnsChanged = true;
        return { ...t, alsoProjectPaths, savedPath, learningPath };
      });
      if (projectPath !== s.projectPath || turnsChanged) {
        next[id] = { ...s, projectPath, turns, updatedAt: Date.now() };
        changed = true;
      } else {
        next[id] = s;
      }
    }
    if (!changed) return;
    this.sessions = next;
    this.persist();
  }

  deleteSession(id: string): void {
    if (!this.sessions[id]) return;
    this.cancelSession(id);
    this.endJob(id);
    const { [id]: _, ...rest } = this.sessions;
    this.sessions = rest;
    if (this.activeSessionId === id) {
      const next = Object.values(rest).sort((a, b) => b.updatedAt - a.updatedAt)[0];
      this.activeSessionId = next?.id ?? null;
      this.focusedTurnId = null;
      this.selectedAgentNode = null;
      this.lastSources = [];
    }
    this.persist();
  }

  /** Cancel + drop every chat bound to a workspace (before deleting its folder). */
  purgeProjectSessions(projectPath: string): void {
    const ids = Object.values(this.sessions)
      .filter((s) => pathsMatch(s.projectPath, projectPath))
      .map((s) => s.id);
    for (const id of ids) this.deleteSession(id);
  }

  /** Wipe all chat/research sessions from memory and localStorage. */
  clearAllSessions(): void {
    for (const id of Object.keys(this.jobs)) {
      this.cancelSession(id);
      this.endJob(id);
    }
    this.sessions = {};
    this.activeSessionId = null;
    this.focusedTurnId = null;
    this.selectedAgentNode = null;
    this.lastSources = [];
    this.activeResearchTurnId = null;
    this.input = "";
    this.ingestSuggestions = [];
    this.viewMode = "mission";
    this.composerMode = "goal";
    if (typeof localStorage !== "undefined") {
      try {
        localStorage.removeItem(SESSIONS_STORAGE_KEY);
        localStorage.removeItem(THREAD_STORAGE_KEY_V1);
      } catch {
        /* ignore */
      }
    }
    this.persist();
  }

  focusTurn(id: string, sessionId?: string): void {
    if (sessionId && this.sessions[sessionId]) {
      this.activeSessionId = sessionId;
    }
    this.focusedTurnId = id;
    app.openAgent();
  }

  /** New research session (empty tab + focus composer). */
  focusNewMission(): void {
    const path = workspace.activeTopicPath;
    if (!path) {
      app.openNewProject();
      return;
    }
    this.createSession({ focus: true, projectPath: path });
  }

  getActiveResearchTurn(): Extract<AssistantTurn, { kind: "research" }> | null {
    const jobTurnId = this.jobs[this.activeSessionId ?? ""]?.turnId;
    const id = jobTurnId ?? this.activeResearchTurnId;
    const thread = this.getThreadForSession(this.activeSessionId);
    if (!id) {
      for (let i = thread.length - 1; i >= 0; i--) {
        const t = thread[i];
        if (t.kind === "research") return t;
      }
      return null;
    }
    const t = thread.find((x) => x.id === id);
    return t?.kind === "research" ? t : null;
  }

  private locateResearchTurn(
    turnId: string,
  ): { turn: Extract<AssistantTurn, { kind: "research" }>; sessionId: string } | null {
    const trySid = (sid: string | null) => {
      if (!sid) return null;
      const found = this.getThreadForSession(sid).find(
        (t): t is Extract<AssistantTurn, { kind: "research" }> =>
          t.id === turnId && t.kind === "research",
      );
      return found ? { turn: found, sessionId: sid } : null;
    };
    const hit = trySid(this.activeSessionId);
    if (hit) return hit;
    for (const s of Object.values(this.sessions)) {
      const found = s.turns.find(
        (t): t is Extract<AssistantTurn, { kind: "research" }> =>
          t.id === turnId && t.kind === "research",
      );
      if (found) return { turn: found, sessionId: s.id };
    }
    return null;
  }

  private resetResearchTurnForRetry(
    turnId: string,
    turn: Extract<AssistantTurn, { kind: "research" }>,
  ): void {
    const scope = turn.retrievalScope ?? this.retrievalScope;
    const runMode = turn.runMode ?? "goal";
    this.updateResearchTurn(turnId, {
      status: "running",
      error: undefined,
      result: undefined,
      savedPath: undefined,
      learningPath: undefined,
      indexed: undefined,
      claimCount: undefined,
      confidence: undefined,
      goalStatus: undefined,
      runId: undefined,
      planExpiresAt: undefined,
      livePlan: undefined,
      liveQueries: undefined,
      liveCritiqueHistory: [],
      looping: false,
      progressStep: "planning",
      progressDetail:
        runMode === "goal"
          ? "Retrying — recalling memory and planning…"
          : "Retrying multi-agent workflow…",
      completedSteps: [],
      showAdvanced: false,
      runMode,
      goalPass: runMode === "goal" ? 1 : undefined,
      goalMaxPasses: runMode === "goal" ? this.maxGoalPasses : undefined,
      agentStatuses: { ...emptyAgentStatuses(), planner: "running" },
      activityLog: [
        {
          id: newId(),
          time: formatLogTime(),
          agent: "system",
          message: "Retrying this run",
          tone: "live",
        },
      ],
      retrievalScope: scope,
    });
  }

  /** Re-run a failed research turn in place — same question, no extra user bubble. */
  async retryResearch(turnId: string): Promise<void> {
    const located = this.locateResearchTurn(turnId);
    if (!located || located.turn.status !== "error") return;
    if (this.sessionBusy(located.sessionId)) return;
    const q = located.turn.query.trim();
    if (!q) return;
    if ((located.turn.runMode ?? "goal") === "studio") {
      await this.runResearch(null, q, {
        skipUserTurn: true,
        retryTurnId: turnId,
        skipPlanReview: true,
        continuePrior: !!located.turn.priorContext,
      });
      return;
    }
    await this.runGoal(q, { skipUserTurn: true, retryTurnId: turnId });
  }

  private getThreadForSession(sessionId: string | null): AssistantTurn[] {
    if (!sessionId) return [];
    return this.sessions[sessionId]?.turns ?? [];
  }

  private hydrate(): void {
    if (this.hydrated || typeof localStorage === "undefined") return;
    this.hydrated = true;
    try {
      const rawV2 = localStorage.getItem(SESSIONS_STORAGE_KEY);
      if (rawV2) {
        const parsed = JSON.parse(rawV2) as SessionsPersist;
        if (parsed && Array.isArray(parsed.sessions)) {
          const map: Record<string, ChatSession> = {};
          let titlesRewritten = false;
          for (const s of parsed.sessions) {
            if (!s?.id) continue;
            const turns = Array.isArray(s.turns)
              ? s.turns.filter((t) => t && (t as { kind?: string }).kind !== "handoff")
              : [];
            const rawTitle = s.title?.trim() || DEFAULT_SESSION_TITLE;
            const folder = folderLabel(s.projectPath ?? null);
            const derived = titleFromSessionTurns(turns);
            const shouldRewrite =
              isPlaceholderSessionTitle(rawTitle, folder) || isTruncatedAutoTitle(rawTitle);
            const title = shouldRewrite ? derived || DEFAULT_SESSION_TITLE : rawTitle;
            if (shouldRewrite && title !== rawTitle) titlesRewritten = true;
            map[s.id] = {
              id: s.id,
              title,
              createdAt: s.createdAt || Date.now(),
              updatedAt: s.updatedAt || Date.now(),
              turns,
              projectPath: s.projectPath ?? null,
              interview: { clarifyCount: s.interview?.clarifyCount ?? 0 },
              draftInput: typeof s.draftInput === "string" ? s.draftInput : "",
              draftAttachments: Array.isArray(s.draftAttachments)
                ? s.draftAttachments
                : [],
            };
          }
          this.sessions = map;
          const active =
            parsed.activeSessionId && this.sessions[parsed.activeSessionId]
              ? parsed.activeSessionId
              : Object.values(this.sessions).sort((a, b) => b.updatedAt - a.updatedAt)[0]?.id ??
                null;
          this.activeSessionId = active;
          this.pruneEmptySessions();
          if (active) this.restoreComposerDraft(active);
          if (titlesRewritten || Object.keys(this.sessions).length !== Object.keys(map).length) {
            this.persist();
          }
          return;
        }
      }

      // Migrate v1 single home thread
      const rawV1 = localStorage.getItem(THREAD_STORAGE_KEY_V1);
      if (rawV1) {
        const turns = JSON.parse(rawV1) as AssistantTurn[];
        if (Array.isArray(turns) && turns.length) {
          const id = newId();
          const now = Date.now();
          this.sessions = {
            [id]: {
              id,
              title: titleFromSessionTurns(turns) || "Migrated session",
              createdAt: now,
              updatedAt: now,
              turns: serializeThread(turns),
            },
          };
          this.activeSessionId = id;
          this.persist();
          try {
            localStorage.removeItem(THREAD_STORAGE_KEY_V1);
          } catch {
            /* ignore */
          }
          return;
        }
      }
    } catch {
      /* ignore */
    }
  }

  private persist(): void {
    if (typeof localStorage === "undefined") return;
    try {
      const payload: SessionsPersist = {
        activeSessionId: this.activeSessionId,
        sessions: Object.values(this.sessions).map((s) => ({
          ...s,
          turns: serializeThread(s.turns),
        })),
      };
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(payload));
    } catch {
      /* ignore quota */
    }
  }

  clearThread(_notePath?: string | null): void {
    const sid = this.activeSessionId;
    if (this.sessionTurnLocked(sid)) return;
    if (!sid || !this.sessions[sid]) return;
    this.patchSession(sid, { turns: [] }, { touchTitle: false });
    this.ensureManagerOpener();
    this.lastSources = [];
    this.activeResearchTurnId = null;
    this.selectedAgentNode = null;
    this.focusedTurnId = null;
    this.persist();
  }

  /** Drop blank New chats except the active one (channel-bound or unbound). */
  private pruneEmptySessions(): void {
    const keep = this.activeSessionId;
    let changed = false;
    const next: Record<string, ChatSession> = {};
    for (const [id, s] of Object.entries(this.sessions)) {
      if (
        shouldDiscardIdleSession(s, {
          isActive: id === keep,
          isBusy: this.sessionBusy(id),
        })
      ) {
        changed = true;
        this.cancelSession(id);
        this.endJob(id);
        continue;
      }
      next[id] = s;
    }
    if (changed) {
      this.sessions = next;
      if (keep && !next[keep]) {
        this.activeSessionId =
          Object.values(next).sort((a, b) => b.updatedAt - a.updatedAt)[0]?.id ?? null;
      }
    }
  }

  private patchSession(
    sessionId: string,
    patch: Partial<Pick<ChatSession, "title" | "turns" | "interview">>,
    opts?: { touchTitle?: boolean },
  ): void {
    const s = this.sessions[sessionId];
    if (!s) return;
    const turns = patch.turns ?? s.turns;
    let title = patch.title ?? s.title;
    if (opts?.touchTitle !== false) {
      const derived = titleFromSessionTurns(turns);
      if (
        derived &&
        (isPlaceholderSessionTitle(title, folderLabel(s.projectPath)) ||
          isTruncatedAutoTitle(title))
      ) {
        title = derived;
      }
    }
    this.sessions = {
      ...this.sessions,
      [sessionId]: {
        ...s,
        ...patch,
        title,
        turns,
        updatedAt: Date.now(),
      },
    };
  }

  private appendTurn(turn: AssistantTurn, sessionId?: string | null): void {
    const sid = sessionId ?? this.ensureActiveSession();
    if (!this.sessions[sid]) return;
    const turns = [...this.getThreadForSession(sid), turn];
    this.patchSession(sid, { turns });
    this.persist();
  }

  appendUser(content: string, sessionId?: string | null): void {
    const text = content.trim();
    if (!text) return;
    const sid = sessionId ?? this.ensureActiveSession();
    this.appendTurn({ id: newId(), kind: "user", content: text }, sid);
    this.clearComposerDraft(sid);
    void this.maybeLlmRenameSession(sid, text);
  }

  /**
   * Async Gemini Flash-Lite rename after the first user message.
   * Keeps heuristic title until the model returns; never overwrites a manual title.
   */
  private async maybeLlmRenameSession(sessionId: string, userText: string): Promise<void> {
    const session = this.sessions[sessionId];
    if (!session) return;
    const folder = folderLabel(session.projectPath ?? null);
    const userTurns = session.turns.filter((t) => t.kind === "user");
    // Only rename on the first real user message
    if (userTurns.length !== 1) return;
    if (!canApplyLlmSessionTitle(session.title, folder, phraseTitleFromText(userText))) {
      return;
    }
    try {
      const res = await api.suggestSessionTitle(userText);
      const next = normalizeLlmSessionTitle(res.title);
      if (!next) return;
      const latest = this.sessions[sessionId];
      if (!latest) return;
      if (
        !canApplyLlmSessionTitle(
          latest.title,
          folderLabel(latest.projectPath ?? null),
          phraseTitleFromText(userText),
        )
      ) {
        return;
      }
      this.patchSession(sessionId, { title: next }, { touchTitle: false });
      this.persist();
    } catch {
      // Heuristic title already applied via patchSession — ignore LLM failures.
    }
  }

  appendManager(content: string, sessionId?: string | null): void {
    const text = content.trim();
    if (!text) return;
    this.appendTurn(
      {
        id: newId(),
        kind: "manager",
        content: text,
      },
      sessionId,
    );
  }

  /** Clear the focused chat without creating a replacement. */
  clearActiveSession(): void {
    this.activeSessionId = null;
    this.focusedTurnId = null;
    this.selectedAgentNode = null;
    this.activeResearchTurnId = null;
    this.routeStatus = null;
    this.lastSources = [];
    this.persist();
  }

  /** Static greeting only on empty channels. */
  ensureManagerOpener(channelEmpty = false): void {
    const sid = this.activeSessionId;
    if (!sid || !this.sessions[sid]) return;
    const s = this.sessions[sid];
    if (!s || !channelEmpty) return;
    // Don't greet once Remember / Ask / Research has started in this chat.
    if (s.turns.some((t) => t.kind !== "manager")) return;
    if (s.turns.length === 0) {
      this.appendTurn({ id: newId(), kind: "manager", content: ONBOARD_OPENER }, sid);
      return;
    }
    if (!s.turns.some((t) => t.kind === "manager")) {
      this.appendTurn({ id: newId(), kind: "manager", content: ONBOARD_OPENER }, sid);
    }
  }

  /** Drop the empty-workspace greeting once notes are being filed. */
  clearOnboardOpener(sessionId?: string | null): void {
    const sid = sessionId ?? this.activeSessionId;
    if (!sid || !this.sessions[sid]) return;
    const s = this.sessions[sid];
    const turns = s.turns.filter(
      (t) => !(t.kind === "manager" && t.content === ONBOARD_OPENER),
    );
    if (turns.length === s.turns.length) return;
    this.patchSession(sid, { turns });
    this.persist();
  }

  clarifyCount(): number {
    return this.activeSession?.interview?.clarifyCount ?? 0;
  }

  bumpClarify(): void {
    const sid = this.ensureActiveSession();
    const cur = this.sessions[sid]?.interview?.clarifyCount ?? 0;
    this.patchSession(sid, { interview: { clarifyCount: cur + 1 } });
    this.persist();
  }

  resetInterview(): void {
    const sid = this.activeSessionId;
    if (!sid || !this.sessions[sid]) return;
    this.patchSession(sid, { interview: { clarifyCount: 0 } });
    this.persist();
  }

  managerHistory(): { role: string; content: string }[] {
    if (this.clarifyCount() < 1) return [];
    const thread = this.getActiveThread();
    let start = -1;
    for (let i = thread.length - 1; i >= 0; i -= 1) {
      const kind = thread[i]?.kind;
      if (kind === "research" || kind === "quick" || kind === "digest") {
        start = i;
        break;
      }
    }
    const window = start >= 0 ? thread.slice(start + 1) : thread;
    return threadToChatMessages(window).map((m) => ({
      role: m.role,
      content: m.content,
    }));
  }

  private updateResearchTurn(
    turnId: string,
    patch: Partial<Extract<AssistantTurn, { kind: "research" }>>,
  ): void {
    const located = this.locateResearchTurn(turnId);
    const sid = located?.sessionId ?? this.activeSessionId;
    if (!sid) return;
    const turns = this.getThreadForSession(sid).map((turn) =>
      turn.id === turnId && turn.kind === "research" ? { ...turn, ...patch } : turn,
    );
    this.patchSession(sid, { turns });
    // Avoid writing localStorage on every stream tick
  }

  private pushActivity(
    turnId: string,
    agent: string,
    message: string,
    tone: ActivityLogEntry["tone"] = "default",
  ): void {
    const sid = this.locateResearchTurn(turnId)?.sessionId ?? this.activeSessionId;
    const turn = this.getThreadForSession(sid).find((t) => t.id === turnId);
    if (turn?.kind !== "research") return;
    const entry: ActivityLogEntry = {
      id: newId(),
      time: formatLogTime(),
      agent,
      message,
      tone,
    };
    const log = [...(turn.activityLog ?? []), entry].slice(-80);
    this.updateResearchTurn(turnId, { activityLog: log });
  }

  private handleStreamEvent(turnId: string, ev: ResearchStreamEvent): void {
    const sid = this.locateResearchTurn(turnId)?.sessionId ?? this.activeSessionId;
    const turn = this.getThreadForSession(sid).find((t) => t.id === turnId);
    if (turn?.kind !== "research") return;

    if (ev.type === "agent_status" && isAgentNode(ev.node)) {
      const statuses = {
        ...(turn.agentStatuses ?? emptyAgentStatuses()),
        [ev.node]: ev.status as AgentNodeStatus,
      };
      const looping = ev.node === "verifier" && ev.status === "iterating";
      const clearLoop =
        (ev.node === "verifier" && ev.status === "done") ||
        (ev.node === "synthesizer" && ev.status === "running");

      const step = (ev.step ? mapStreamStep(ev.step) : NODE_TO_STEP[ev.node]) as ResearchProgressStep;
      const completed = [...(turn.completedSteps ?? [])];
      if (ev.status === "done" || ev.status === "iterating") {
        const prevStep = turn.progressStep;
        if (prevStep && prevStep !== step && !completed.includes(prevStep)) {
          completed.push(prevStep);
        }
        if (ev.status === "done" && !completed.includes(step)) {
          completed.push(step);
        }
      }

      this.updateResearchTurn(turnId, {
        agentStatuses: statuses,
        progressStep: ev.status === "running" ? step : turn.progressStep,
        progressDetail: ev.detail || turn.progressDetail,
        completedSteps: Array.from(new Set(completed)),
        looping: clearLoop ? false : looping || turn.looping,
      });

      if (ev.status === "running") {
        this.pushActivity(
          turnId,
          ev.label || ev.node,
          statusLineForAgent(ev.node, "running", ev.detail),
          "live",
        );
        this.touchUiForSession(sid!, { selectedAgentNode: ev.node });
      } else if (ev.status === "iterating") {
        this.pushActivity(
          turnId,
          ev.label || ev.node,
          statusLineForAgent(ev.node, "iterating", ev.detail),
          "warning",
        );
      } else if (ev.status === "error") {
        this.pushActivity(
          turnId,
          ev.label || ev.node,
          statusLineForAgent(ev.node, "error", ev.detail),
          "error",
        );
      } else if (ev.status === "done") {
        this.pushActivity(
          turnId,
          ev.label || ev.node,
          statusLineForAgent(ev.node, "done", ev.detail),
          "success",
        );
      }
      return;
    }

    if (ev.type === "stage") {
      const step = mapStreamStep(ev.step);
      const stepOrder = RESEARCH_STEPS.map((s) => s.id);
      const prev = turn.progressStep;
      const nextCompleted = [...(turn.completedSteps ?? [])];
      if (prev !== step) nextCompleted.push(prev);

      let statuses = turn.agentStatuses;
      if (!statuses || Object.values(statuses).every((s) => s === "pending")) {
        statuses = statusesFromCompletedSteps(nextCompleted, step);
      }

      this.updateResearchTurn(turnId, {
        progressStep: step,
        progressDetail: ev.detail || undefined,
        completedSteps: Array.from(new Set(nextCompleted)).filter((s) =>
          stepOrder.includes(s),
        ) as ResearchProgressStep[],
        agentStatuses: statuses,
      });

      if (!turn.activityLog?.some((l) => l.message === (ev.detail || step))) {
        this.pushActivity(turnId, ev.label || ev.node || step, ev.detail || step, "default");
      }
      return;
    }

    if (ev.type === "plan") {
      this.updateResearchTurn(turnId, {
        livePlan: ev.plan,
        liveQueries: ev.retrieval_queries ?? [],
      });
      this.pushActivity(turnId, "Planner", "Plan ready", "success");
      return;
    }

    if (ev.type === "artifact") {
      if (ev.kind === "retrieval") {
        this.pushActivity(
          turnId,
          "Retriever",
          retrievalStatsLine(ev.retrieval_stats as Record<string, number> | undefined),
          "success",
        );
      } else if (ev.kind === "analysis") {
        this.pushActivity(turnId, "Analyst", "Analyst finished — draft insights ready", "success");
      }
      return;
    }

    if (ev.type === "memory") {
      this.updateResearchTurn(turnId, {
        memoryRecalled:
          ev.phase === "recalled"
            ? (ev.recalled_count ?? turn.memoryRecalled)
            : turn.memoryRecalled,
        memoryDetail: ev.detail || turn.memoryDetail,
        learningPath: ev.learning_path || turn.learningPath,
        savedPath: ev.report_path || turn.savedPath,
        confidence: ev.confidence ?? turn.confidence,
      });
      this.pushActivity(
        turnId,
        "Memory",
        ev.detail || (ev.phase === "written" ? "Wrote learning card" : "Recalled memory"),
        "success",
      );
      return;
    }

    if (ev.type === "goal_pass") {
      this.updateResearchTurn(turnId, {
        goalPass: ev.pass ?? turn.goalPass,
        goalMaxPasses: ev.max_passes ?? turn.goalMaxPasses,
        progressDetail: ev.detail || `Goal pass ${ev.pass}/${ev.max_passes}`,
      });
      this.pushActivity(
        turnId,
        "Goal",
        ev.detail || `Pass ${ev.pass}/${ev.max_passes}`,
        "live",
      );
      // Reset agent statuses for a new pass so the graph animates again
      if ((ev.pass ?? 1) > 1) {
        this.updateResearchTurn(turnId, {
          agentStatuses: { ...emptyAgentStatuses(), planner: "running" },
          looping: false,
        });
      }
      return;
    }

    if (ev.type === "goal_status") {
      this.updateResearchTurn(turnId, {
        goalStatus: ev.status,
        confidence: ev.confidence ?? turn.confidence,
        progressDetail: ev.detail || `Goal ${ev.status}`,
      });
      this.pushActivity(turnId, "Goal", ev.detail || String(ev.status), "success");
      return;
    }

    if (ev.type === "critique") {
      const history = [...(turn.liveCritiqueHistory ?? [])];
      if (ev.history_entry) history.push(ev.history_entry);
      this.updateResearchTurn(turnId, {
        liveCritiqueHistory: history,
        looping: ev.critique_approved ? false : true,
      });
      const verdict = ev.critique_approved ? "Approved" : "Revise";
      this.pushActivity(
        turnId,
        "Verifier",
        `${verdict}${ev.critique ? `: ${ev.critique.slice(0, 120)}` : ""}`,
        ev.critique_approved ? "success" : "warning",
      );
      return;
    }
  }

  private abortFor(sessionId: string | null): AbortSignal | undefined {
    if (!sessionId) return undefined;
    return this.jobs[sessionId]?.abort.signal;
  }

  buildPriorContext(sessionId?: string | null): string | undefined {
    const sid = sessionId ?? this.activeSessionId;
    const thread = this.getThreadForSession(sid);
    const chunks: string[] = [];
    for (let i = thread.length - 1; i >= 0 && chunks.length < 2; i--) {
      const t = thread[i];
      if (t.kind === "research" && t.status === "done" && t.result) {
        const report = t.result.report.slice(0, 2200);
        const plan = (t.result.plan || "").slice(0, 600);
        const saved = t.savedPath || t.result.saved_path;
        const savedLine = saved ? `\nSaved note path: ${saved}` : "";
        chunks.push(
          `Previous question: ${t.result.query}\nPlan:\n${plan}${savedLine}\nReport excerpt:\n${report}`,
        );
      }
    }
    if (!chunks.length) return undefined;
    return chunks.reverse().join("\n\n---\n\n").slice(0, 3500);
  }

  /** Bound topic for this chat only. Unbound chats do not inherit the workspace folder. */
  activeProjectPath(): string | null {
    return this.activeSession?.projectPath ?? null;
  }

  continueFromLastResearch(): void {
    const prior = this.buildPriorContext();
    if (!prior) return;
    const thread = this.getActiveThread();
    const last = [...thread].reverse().find((t) => t.kind === "research" && t.status === "done");
    if (last && last.kind === "research") {
      this.input = `Continue and deepen the previous research on: ${last.query}`;
    }
  }

  setIngestSuggestions(suggestions: string[]): void {
    this.ingestSuggestions = suggestions;
  }

  cancelResearch(): void {
    if (this.activeSessionId) this.cancelSession(this.activeSessionId);
  }

  selectAgentNode(node: AgentNodeId | null): void {
    this.selectedAgentNode = node;
  }

  async sendQuickAnswer(
    _notePath: string | null,
    context: ChatContext,
    question?: string,
    opts?: { skipUserTurn?: boolean; alsoProjectPaths?: string[]; sessionId?: string | null },
  ): Promise<{ thinMemory: boolean }> {
    const q = (question ?? this.input).trim();
    const sid = opts?.sessionId ?? this.ensureActiveSession();
    if (!q || !sid || !this.sessions[sid] || this.sessionBusy(sid)) {
      return { thinMemory: false };
    }

    const attachedNames = this.attachments.map((a) => a.name);
    this.input = "";
    this.attachments = [];
    this.composerMode = "quick";
    this.touchUiForSession(sid, { viewMode: "ask", routeStatus: "explain" });
    app.openAgent();

    if (!opts?.skipUserTurn) {
      const shown = attachedNames.length
        ? `${q}\n\nAttached (this question only): ${attachedNames.join(", ")}`
        : q;
      this.appendTurn({ id: newId(), kind: "user", content: shown }, sid);
    }

    const thread = this.getThreadForSession(sid);
    const messages = threadToChatMessages(thread);
    if (messages.at(-1)?.role !== "user") {
      messages.push({ role: "user", content: q });
    }

    const started = this.beginJob(sid, "quick");
    if ("error" in started) return { thinMemory: false };
    try {
      const result = await api.chat(messages, context, 5, {
        projectPath: this.projectPathForSession(sid),
        sessionId: sid,
        alsoProjectPaths: opts?.alsoProjectPaths,
      });
      const thin = !!result.thin_memory;
      this.appendTurn(
        {
          id: newId(),
          kind: "quick",
          role: "assistant",
          content: result.answer,
          sources: result.sources,
          thinMemory: thin,
        },
        sid,
      );
      const contested = result.contested_claims ?? [];
      if (contested.length) {
        const first = (contested[0]?.claim || "a finding").trim().slice(0, 120);
        this.appendTurn(
          {
            id: newId(),
            kind: "manager",
            content:
              contested.length === 1
                ? `Your notes disagree with a later finding: ${first}`
                : `Your notes disagree on ${contested.length} points. First: ${first}`,
          },
          sid,
        );
      }
      if (this.activeSessionId === sid) {
        this.lastSources = result.sources;
        this.routeStatus = null;
      }
      return { thinMemory: thin };
    } catch (e) {
      const message = e instanceof Error ? e.message : "Quick answer failed";
      this.appendTurn(
        {
          id: newId(),
          kind: "quick",
          role: "assistant",
          content: "",
          sources: [],
          error: message,
        },
        sid,
      );
      this.touchUiForSession(sid, { routeStatus: null });
      return { thinMemory: false };
    } finally {
      this.endJob(sid, started.abort);
      this.persist();
    }
  }

  /** Re-ask a failed quick turn without duplicating the user bubble. */
  async retryQuickAnswer(turnId: string, context: ChatContext): Promise<void> {
    const located = this.locateAnyTurn(turnId);
    const sid = located?.sessionId ?? this.activeSessionId;
    if (!sid || this.sessionBusy(sid)) return;
    const thread = this.getThreadForSession(sid);
    const idx = thread.findIndex((t) => t.id === turnId);
    const turn = thread[idx];
    if (!turn || turn.kind !== "quick" || !turn.error) return;
    let q = "";
    for (let i = idx - 1; i >= 0; i -= 1) {
      const prev = thread[i];
      if (prev?.kind === "user") {
        q = prev.content.replace(/\n\nAttached \(this question only\):.*$/s, "").trim();
        break;
      }
    }
    if (!q) return;
    this.patchSession(sid, { turns: thread.filter((t) => t.id !== turnId) });
    await this.sendQuickAnswer(null, context, q, { skipUserTurn: true, sessionId: sid });
  }

  /** Off-topic refuse: no Goal, optional Look this up in the thread. */
  presentRefuse(
    userText: string,
    answer: string,
    opts?: { skipUserTurn?: boolean; sessionId?: string | null },
  ): void {
    const q = userText.trim();
    if (!q) return;
    const sid = opts?.sessionId ?? this.ensureActiveSession();
    if (!sid || !this.sessions[sid]) return;
    this.input = "";
    this.attachments = [];
    this.composerMode = "quick";
    this.touchUiForSession(sid, { viewMode: "ask", routeStatus: null });
    app.openAgent();
    if (!opts?.skipUserTurn) {
      this.appendTurn({ id: newId(), kind: "user", content: q }, sid);
    }
    this.appendTurn(
      {
        id: newId(),
        kind: "quick",
        role: "assistant",
        content: answer,
        sources: [],
        thinMemory: true,
      },
      sid,
    );
    this.persist();
  }

  addAttachment(file: Omit<ComposerAttachment, "id"> & { id?: string }): void {
    const id = file.id ?? newId();
    if (file.path && this.attachments.some((a) => a.path === file.path)) return;

    const sameNameIdx = this.attachments.findIndex((a) => a.name === file.name);
    if (sameNameIdx >= 0) {
      const existing = this.attachments[sameNameIdx];
      // Prefer a path-backed attachment over a browser File blob of the same name.
      if (existing.path && !file.path) return;
      if (!existing.path && file.path) {
        const next = [...this.attachments];
        next[sameNameIdx] = { ...file, id: existing.id };
        this.attachments = next;
        return;
      }
      if (!existing.path && !file.path && existing.text === file.text) return;
    }

    this.attachments = [...this.attachments, { ...file, id }];
  }

  removeAttachment(id: string): void {
    this.attachments = this.attachments.filter((a) => a.id !== id);
  }

  clearAttachments(): void {
    this.attachments = [];
  }

  /** File notes already in the topic (imports). Does not use the vault watcher. */
  async rememberTopicNotes(topicPath?: string | null): Promise<void> {
    const topic = topicPath ?? this.activeProjectPath();
    if (!topic) return;
    this.ensureActiveSession();
    this.setSessionProject(topic);
    const files = flattenVaultFiles(await loadVaultTree(topic))
      .map((f) => f.path)
      .filter(isRememberableNotePath)
      .sort((a, b) => a.localeCompare(b));
    if (!files.length) {
      this.ensureActiveSession();
      const turnId = newId();
      this.appendTurn({
        id: turnId,
        kind: "digest",
        status: "error",
        label: "Remember topic notes",
        error: "No notes in this topic to file. Attach markdown or dump in the composer.",
      });
      this.persist();
      return;
    }
    await this.runDigest({
      paths: files,
      title: `Remember notes in ${topic.split(/[\\/]/).pop() ?? "topic"}`,
    });
    workspace.requestVaultRefresh();
  }

  /**
   * If the folder has markdown but no memory claims yet, file them once.
   * Dropping files into the vault does not fill Ask memory until Teach runs.
   */
  async ensureUnfiledNotesRemembered(topicPath?: string | null): Promise<void> {
    const topic = (topicPath ?? this.activeProjectPath() ?? "").trim();
    if (!topic) return;
    const key = topic.replace(/[/\\]+$/, "").toLowerCase();
    if (this._rememberAttempted.has(key)) return;
    try {
      const { topicHasUnfiledNotes } = await import("$lib/vault/load");
      if (!(await topicHasUnfiledNotes(topic))) return;
    } catch {
      return;
    }
    this._rememberAttempted.add(key);
    await this.rememberTopicNotes(topic);
  }

  private _rememberAttempted = new Set<string>();

  async runDigest(opts?: {
    text?: string;
    paths?: string[];
    title?: string;
    sessionId?: string | null;
  }): Promise<void> {
    const text = (opts?.text ?? this.input).trim();
    const paths = opts?.paths ?? this.attachments.map((a) => a.path).filter((p): p is string => !!p);
    const untitledText = this.attachments
      .filter((a) => a.text && !a.path)
      .map((a) => a.text)
      .join("\n\n");
    const body = [text, untitledText].filter(Boolean).join("\n\n");
    if ((!body && paths.length === 0)) return;
    const sid = opts?.sessionId ?? this.ensureActiveSession();
    if (!sid || !this.sessions[sid] || this.sessionBusy(sid)) return;

    this.clearOnboardOpener(sid);
    this.input = "";
    this.attachments = [];
    app.openAgent();
    this.touchUiForSession(sid, { routeStatus: "teach" });

    const label = body
      ? truncateSessionTitle(body)
      : `Remember ${paths.map((p) => p.split(/[\\/]/).pop()).join(", ")}`;
    const turnId = newId();
    this.appendTurn(
      {
        id: turnId,
        kind: "digest",
        status: "running",
        label,
        retryText: body || undefined,
        retryPaths: paths,
      },
      sid,
    );

    const started = this.beginJob(sid, "digest", { turnId });
    if ("error" in started) {
      this.updateTurn(
        turnId,
        {
          kind: "digest",
          status: "error",
          label,
          error: "This chat is already busy.",
          retryText: body || undefined,
          retryPaths: paths,
        },
        sid,
      );
      return;
    }
    try {
      const result: DigestResult = await api.digest(
        {
          text: body || null,
          title: opts?.title ?? label,
          paths: paths.length ? paths : undefined,
          projectPath: this.projectPathForSession(sid),
          sessionId: sid,
        },
        started.abort.signal,
      );
      this.updateTurn(
        turnId,
        {
          kind: "digest",
          status: "done",
          label,
          savedPath: result.saved_path,
          contentHash: result.content_hash,
          idempotent: result.idempotent,
          claimsCreated: result.claims_created,
          claimsRevised: result.claims_revised,
          claimsDropped: result.claims_dropped,
          linkedSources: result.linked_sources,
          summary: result.summary,
          retryText: body || undefined,
          retryPaths: paths,
        },
        sid,
      );
      this.appendTeachAskNudge(sid, result.claims_created, result.claims_revised);
    } catch (e) {
      const aborted = e instanceof Error && e.name === "AbortError";
      this.updateTurn(
        turnId,
        {
          kind: "digest",
          status: "error",
          label,
          error: aborted ? "Cancelled" : e instanceof Error ? e.message : "Remember failed",
          retryText: body || undefined,
          retryPaths: paths,
        },
        sid,
      );
    } finally {
      this.endJob(sid, started.abort);
      this.touchUiForSession(sid, { routeStatus: null });
      this.persist();
    }
  }

  /** Re-file a failed remember turn without a new user bubble. */
  async retryDigest(turnId: string): Promise<void> {
    const located = this.locateAnyTurn(turnId);
    const sid = located?.sessionId ?? this.activeSessionId;
    if (!sid || this.sessionBusy(sid)) return;
    const turn = this.getThreadForSession(sid).find((t) => t.id === turnId);
    if (!turn || turn.kind !== "digest" || turn.status !== "error") return;
    const body = (turn.retryText ?? "").trim();
    const paths = turn.retryPaths ?? [];
    if (!body && paths.length === 0) return;

    this.touchUiForSession(sid, { routeStatus: "teach" });
    this.updateTurn(
      turnId,
      {
        kind: "digest",
        status: "running",
        label: turn.label,
        error: undefined,
        retryText: body || undefined,
        retryPaths: paths,
      },
      sid,
    );
    const started = this.beginJob(sid, "digest", { turnId });
    if ("error" in started) return;
    try {
      const result: DigestResult = await api.digest(
        {
          text: body || null,
          title: turn.label,
          paths: paths.length ? paths : undefined,
          projectPath: this.projectPathForSession(sid),
          sessionId: sid,
        },
        started.abort.signal,
      );
      this.updateTurn(
        turnId,
        {
          kind: "digest",
          status: "done",
          label: turn.label,
          savedPath: result.saved_path,
          contentHash: result.content_hash,
          idempotent: result.idempotent,
          claimsCreated: result.claims_created,
          claimsRevised: result.claims_revised,
          claimsDropped: result.claims_dropped,
          linkedSources: result.linked_sources,
          summary: result.summary,
          retryText: body || undefined,
          retryPaths: paths,
        },
        sid,
      );
      this.appendTeachAskNudge(sid, result.claims_created, result.claims_revised);
    } catch (e) {
      const aborted = e instanceof Error && e.name === "AbortError";
      this.updateTurn(
        turnId,
        {
          kind: "digest",
          status: "error",
          label: turn.label,
          error: aborted ? "Cancelled" : e instanceof Error ? e.message : "Remember failed",
          retryText: body || undefined,
          retryPaths: paths,
        },
        sid,
      );
    } finally {
      this.endJob(sid, started.abort);
      this.touchUiForSession(sid, { routeStatus: null });
      this.persist();
    }
  }

  private appendTeachAskNudge(
    sid: string,
    created?: number | null,
    revised?: number | null,
  ): void {
    const n = (created ?? 0) + (revised ?? 0);
    const channel =
      folderLabel(this.sessions[sid]?.projectPath ?? null) || "this topic";
    const ideas = n === 1 ? "1 idea" : `${Math.max(n, 0)} ideas`;
    this.appendTurn(
      {
        id: newId(),
        kind: "manager",
        content: `Remembered ${ideas} into #${channel} memory. Ask me about them when you're ready.`,
      },
      sid,
    );
  }

  private locateAnyTurn(
    turnId: string,
  ): { sessionId: string; turn: AssistantTurn } | null {
    for (const s of Object.values(this.sessions)) {
      const turn = s.turns.find((t) => t.id === turnId);
      if (turn) return { sessionId: s.id, turn };
    }
    return null;
  }

  private updateTurn(
    turnId: string,
    patch: Partial<AssistantTurn> & { kind?: AssistantTurn["kind"] },
    sessionId?: string | null,
  ): void {
    const sid = sessionId ?? this.locateAnyTurn(turnId)?.sessionId ?? this.activeSessionId;
    if (!sid) return;
    const turns = this.getThreadForSession(sid).map((turn) =>
      turn.id === turnId ? ({ ...turn, ...patch } as AssistantTurn) : turn,
    );
    this.patchSession(sid, { turns });
  }

  private projectPathForSession(sessionId: string | null | undefined): string | null {
    if (!sessionId) return this.activeProjectPath();
    return this.sessions[sessionId]?.projectPath ?? null;
  }

  private touchUiForSession(
    sessionId: string,
    patch: {
      routeStatus?: "teach" | "explain" | "lookup" | null;
      viewMode?: "ask" | "mission" | "report";
      focusedTurnId?: string | null;
      activeResearchTurnId?: string | null;
      selectedAgentNode?: AgentNodeId | null;
    },
  ): void {
    if (this.activeSessionId !== sessionId) return;
    if (patch.routeStatus !== undefined) this.routeStatus = patch.routeStatus;
    if (patch.viewMode !== undefined) this.viewMode = patch.viewMode;
    if (patch.focusedTurnId !== undefined) this.focusedTurnId = patch.focusedTurnId;
    if (patch.activeResearchTurnId !== undefined) {
      this.activeResearchTurnId = patch.activeResearchTurnId;
    }
    if (patch.selectedAgentNode !== undefined) {
      this.selectedAgentNode = patch.selectedAgentNode;
    }
  }

  private async finalizeResearchResult(
    turnId: string,
    result: ResearchResult,
  ): Promise<void> {
    let savedPath: string | undefined =
      result.report_path || result.saved_path || undefined;
    let learningPath: string | undefined = result.learning_path || undefined;
    let indexed = !!(result.report_path || result.learning_path);
    let clientReportOnly = false;

    // Prefer server-side memory write; fall back to desktop save+index
    // unless the server already decided this lookup should not be filed.
    if (!savedPath && shouldSaveResearchToVault(result)) {
      try {
        const saved = await saveAndIndexResearch(result, {
          projectPath: this.activeProjectPath(),
        });
        savedPath = saved.path;
        indexed = saved.indexed;
        clientReportOnly = true;
        result = { ...result, saved_path: savedPath };
      } catch {
        /* save optional */
      }
    }

    const finalStatuses = emptyAgentStatuses();
    for (const id of Object.keys(finalStatuses) as AgentNodeId[]) {
      finalStatuses[id] = "done";
    }

    const sid = this.locateResearchTurn(turnId)?.sessionId ?? this.activeSessionId;
    const priorTurn = this.getThreadForSession(sid).find(
      (t): t is Extract<AssistantTurn, { kind: "research" }> =>
        t.id === turnId && t.kind === "research",
    );
    const critiqueHistory =
      result.critique_history?.length
        ? result.critique_history
        : priorTurn?.liveCritiqueHistory;

    const memoryFiled =
      !!learningPath ||
      (result.claim_count ?? 0) > 0 ||
      result.memory_written === true;

    let memoryDetail: string | undefined;
    if (result.memory_detail) {
      memoryDetail = result.memory_detail;
    } else if (memoryFiled) {
      memoryDetail = result.claim_count
        ? `Updated chat memory · ${result.claim_count} claim(s) · linked to project`
        : "Updated chat memory · linked to project";
    } else if (clientReportOnly && savedPath) {
      memoryDetail = "Report saved to library";
    } else {
      memoryDetail = priorTurn?.memoryDetail;
    }

    this.updateResearchTurn(turnId, {
      status: "done",
      progressStep: "writing",
      progressDetail: memoryDetail || (savedPath ? "Report saved to library" : "Report complete"),
      completedSteps: RESEARCH_STEPS.map((s) => s.id),
      result,
      savedPath,
      learningPath,
      indexed,
      confidence: result.confidence ?? undefined,
      goalStatus: result.goal_status ?? undefined,
      memoryDetail: memoryDetail || undefined,
      claimCount: result.claim_count ?? undefined,
      agentStatuses: finalStatuses,
      looping: false,
      liveCritiqueHistory: critiqueHistory,
      livePlan: result.plan,
      liveQueries: result.retrieval_queries,
    });

    const contested = result.contested_claims ?? [];
    if (contested.length) {
      const first = (contested[0]?.claim || "a finding").trim().slice(0, 120);
      const sidForMsg = sid ?? this.activeSessionId;
      if (sidForMsg) {
        const turns = [
          ...this.getThreadForSession(sidForMsg),
          {
            id: newId(),
            kind: "manager" as const,
            content:
              contested.length === 1
                ? `Your notes disagree with this run: ${first}`
                : `Your notes disagree with this run on ${contested.length} claims. First: ${first}`,
          },
        ];
        this.patchSession(sidForMsg, { turns });
      }
    }

    const claimCount = result.claim_count ?? 0;
    if (claimCount > 0 && sid) {
      const channelName =
        folderLabel(this.sessions[sid]?.projectPath ?? null) || "workspace";
      const noun = claimCount === 1 ? "claim" : "claims";
      const turns = [
        ...this.getThreadForSession(sid),
        {
          id: newId(),
          kind: "manager" as const,
          content: `Filed ${claimCount} ${noun} into #${channelName} memory.`,
        },
      ];
      this.patchSession(sid, { turns });
    }

    if (savedPath || learningPath || indexed) {
      workspace.requestVaultRefresh();
    }
    this.pushActivity(turnId, "system", "Mission complete", "success");
    const doneSid = this.locateResearchTurn(turnId)?.sessionId;
    if (doneSid) {
      this.touchUiForSession(doneSid, {
        focusedTurnId: turnId,
        viewMode: "mission",
      });
    }
    // Details stay closed — user opens from the run block
    if (this.activeSessionId === doneSid) {
      this.inspectorOpen = false;
    }
    workspace.requestVaultRefresh();
    await connection.refreshStatus();
    this.persist();
  }

  private researchErrorMessage(e: unknown, sessionId?: string | null): string {
    const raw = e instanceof Error ? e.message : String(e ?? "Research failed");
    if (raw === "STREAM_UNAVAILABLE" || /STREAM_UNAVAILABLE/i.test(raw)) {
      return (
        "Research stream not available on the sidecar (404). " +
        "Restart the app or run ./scripts/start_sidecar.sh so it loads the latest API " +
        "(/api/research/stream and /api/goals/stream)."
      );
    }
    const aborted = e instanceof Error && e.name === "AbortError";
    if (aborted) {
      const cancelled = sessionId ? !!this.jobs[sessionId]?.cancelledByUser : false;
      return cancelled
        ? "Research cancelled"
        : `Research timed out after ${RESEARCH_TIMEOUT_MS / 60_000} minutes — try a shorter question or use Quick answer`;
    }
    // WebKit/Safari fetch network failures
    if (
      raw === "Load failed" ||
      raw === "Failed to fetch" ||
      /networkerror|network request failed/i.test(raw)
    ) {
      return (
        "Could not reach the research service (sidecar). " +
        "Restart with ./scripts/start_sidecar.sh, check Settings → Providers " +
        "(OpenRouter key + model), then retry."
      );
    }
    if (/Unknown LLM_PROVIDER/i.test(raw)) {
      return (
        "AI provider not loaded by the sidecar. Restart the sidecar after changing providers, " +
        "then ensure OpenRouter is connected with a valid key."
      );
    }
    if (/API key is not set/i.test(raw)) {
      return (
        "No API key for the active provider. Settings → Providers → Connect OpenRouter " +
        "and paste your sk-or-… key, then Use that provider."
      );
    }
    if (/too many research graphs|max \d+/i.test(raw)) {
      return RESEARCH_CAP_MESSAGE;
    }
    return raw;
  }

  async runGoal(
    goal?: string,
    opts?: {
      skipUserTurn?: boolean;
      retryTurnId?: string;
      alsoProjectPaths?: string[];
      sessionId?: string | null;
    },
  ): Promise<void> {
    const retrying = !!opts?.retryTurnId;
    const located = opts?.retryTurnId ? this.locateResearchTurn(opts.retryTurnId) : null;
    const q = (goal ?? located?.turn.query ?? this.input).trim();
    const sid =
      opts?.sessionId ?? located?.sessionId ?? this.ensureActiveSession();
    if (!q || !sid || !this.sessions[sid] || this.sessionBusy(sid)) return;
    const alsoProjectPaths = opts?.alsoProjectPaths ?? located?.turn.alsoProjectPaths ?? [];

    if (!retrying) {
      this.input = "";
      this.composerMode = "goal";
    }
    app.openAgent();
    this.inspectorOpen = false;
    this.ingestSuggestions = [];
    this.touchUiForSession(sid, {
      viewMode: "mission",
      routeStatus: "lookup",
    });

    const projectPath = this.projectPathForSession(sid);
    const scope = located?.turn.retrievalScope ?? this.retrievalScope;
    if (!opts?.skipUserTurn && !retrying) {
      const userTurn: AssistantTurn = { id: newId(), kind: "user", content: q };
      this.appendTurn(userTurn, sid);
    }

    const turnId = located?.turn.id ?? newId();
    this.touchUiForSession(sid, {
      focusedTurnId: turnId,
      activeResearchTurnId: turnId,
      selectedAgentNode: "planner",
    });

    if (located) {
      this.resetResearchTurnForRetry(turnId, located.turn);
    } else {
      this.appendTurn(
        {
          id: turnId,
          kind: "research",
          query: q,
          status: "running",
          progressStep: "planning",
          progressDetail: "Goal mode · recalling memory and planning…",
          completedSteps: [],
          showAdvanced: false,
          runMode: "goal",
          goalPass: 1,
          goalMaxPasses: this.maxGoalPasses,
          agentStatuses: { ...emptyAgentStatuses(), planner: "running" },
          activityLog: [
            {
              id: newId(),
              time: formatLogTime(),
              agent: "system",
              message: `Goal started · up to ${this.maxGoalPasses} passes · scope ${scope}`,
              tone: "live",
            },
          ],
          liveCritiqueHistory: [],
          looping: false,
          retrievalScope: scope,
          alsoProjectPaths,
        },
        sid,
      );
    }

    const started = this.beginJob(sid, "research", {
      turnId,
      timeoutMs: RESEARCH_TIMEOUT_MS,
    });
    if ("error" in started) {
      this.updateResearchTurn(turnId, { status: "error", error: RESEARCH_CAP_MESSAGE });
      this.pushActivity(turnId, "system", RESEARCH_CAP_MESSAGE, "error");
      this.persist();
      return;
    }

    try {
      let result: ResearchResult;
      try {
        result = await api.goalStream(
          q,
          (ev) => this.handleStreamEvent(turnId, ev),
          this.abortFor(sid)!,
          {
            retrievalScope: scope,
            projectPath,
            sessionId: sid,
            maxPasses: this.maxGoalPasses,
            alsoProjectPaths,
          },
        );
      } catch (streamErr) {
        if (streamErr instanceof Error && streamErr.name === "AbortError") throw streamErr;
        // Old sidecar without /api/goals/stream (404), or stream failure → multi-pass via research stream
        this.pushActivity(
          turnId,
          "system",
          "Goal stream unavailable — using research stream multi-pass (restart sidecar for full goal API)",
          "warning",
        );
        result = await this.runGoalViaResearchStream(
          turnId,
          q,
          scope,
          projectPath,
          sid,
          alsoProjectPaths,
        );
      }
      await this.finalizeResearchResult(turnId, result);
    } catch (e) {
      const message = this.researchErrorMessage(e, sid);
      this.updateResearchTurn(turnId, {
        status: "error",
        error: message,
        progressDetail: message,
      });
      this.pushActivity(turnId, "system", message, "error");
    } finally {
      this.endJob(sid, started.abort);
      this.touchUiForSession(sid, { routeStatus: null });
      if (this.activeResearchTurnId === turnId) {
        this.activeResearchTurnId = this.jobs[this.activeSessionId ?? ""]?.turnId ?? null;
      }
      this.persist();
    }
  }

  /** Client-side goal loop when /api/goals/stream is missing (old sidecar). */
  private async runGoalViaResearchStream(
    turnId: string,
    goal: string,
    scope: RetrievalScope,
    projectPath: string | null,
    sessionId: string | null,
    alsoProjectPaths: string[] = [],
  ): Promise<ResearchResult> {
    const maxPasses = Math.max(1, Math.min(4, this.maxGoalPasses));
    let query = goal;
    let priorContext: string | undefined;
    let last: ResearchResult | null = null;
    const passes: NonNullable<ResearchResult["passes"]> = [];

    for (let pass = 1; pass <= maxPasses; pass++) {
      this.handleStreamEvent(turnId, {
        type: "goal_pass",
        pass,
        max_passes: maxPasses,
        reason: pass === 1 ? "initial" : "deepen_open_questions",
        query: query.slice(0, 240),
        detail: `Goal pass ${pass}/${maxPasses}`,
      });

      let result: ResearchResult;
      try {
        result = await api.researchStream(
          query,
          (ev) => this.handleStreamEvent(turnId, ev),
          this.abortFor(sessionId),
          priorContext,
          scope,
          projectPath,
          sessionId,
          alsoProjectPaths,
        );
      } catch (streamErr) {
        if (streamErr instanceof Error && streamErr.name === "AbortError") throw streamErr;
        this.pushActivity(turnId, "system", "Stream failed — non-stream research", "warning");
        result = await api.research(
          query,
          this.abortFor(sessionId),
          priorContext,
          scope,
          projectPath,
          sessionId,
          alsoProjectPaths,
        );
      }

      last = result;
      const conf = result.confidence ?? 0;
      const openQ = result.open_questions ?? [];
      passes.push({
        pass,
        query,
        confidence: conf,
        open_questions: openQ,
        learning_path: result.learning_path,
        report_path: result.report_path,
        revision_count: result.revision_count,
      });

      const shouldContinue =
        pass < maxPasses && (conf < 0.65 || openQ.length >= 2);
      if (!shouldContinue) {
        const status = conf >= 0.65 ? "completed" : "partial";
        this.handleStreamEvent(turnId, {
          type: "goal_status",
          status,
          stop_reason: shouldContinue ? "max_passes_reached" : "goal_satisfied",
          pass_count: pass,
          max_passes: maxPasses,
          confidence: conf,
          detail: `Goal ${status} after ${pass} pass(es)`,
        });
        return {
          ...result,
          query: goal,
          goal,
          goal_status: status,
          goal_stop_reason: pass >= maxPasses ? "max_passes_reached" : "goal_satisfied",
          passes,
          pass_count: passes.length,
        };
      }

      priorContext = (result.report || "").slice(0, 3500);
      const bullets =
        openQ.slice(0, 3).map((x) => `- ${x}`).join("\n") ||
        "- Deepen coverage and evidence quality";
      query =
        `${goal}\n\nFocus this pass on remaining gaps:\n${bullets}\n\n` +
        `Prior findings to build on:\n${(result.report || "").slice(0, 800)}`;
    }

    // Exhausted passes
    const final = last!;
    this.handleStreamEvent(turnId, {
      type: "goal_status",
      status: "partial",
      stop_reason: "max_passes_reached",
      pass_count: maxPasses,
      max_passes: maxPasses,
      confidence: final.confidence ?? 0,
      detail: `Goal partial after ${maxPasses} pass(es)`,
    });
    return {
      ...final,
      query: goal,
      goal,
      goal_status: "partial",
      goal_stop_reason: "max_passes_reached",
      passes,
      pass_count: passes.length,
    };
  }

  async runResearch(
    _notePath: string | null,
    query?: string,
    opts?: {
      continuePrior?: boolean;
      skipPlanReview?: boolean;
      skipUserTurn?: boolean;
      retryTurnId?: string;
      alsoProjectPaths?: string[];
      sessionId?: string | null;
    },
  ): Promise<void> {
    const retrying = !!opts?.retryTurnId;
    const located = opts?.retryTurnId ? this.locateResearchTurn(opts.retryTurnId) : null;
    const q = (query ?? located?.turn.query ?? this.input).trim();
    const sid =
      opts?.sessionId ?? located?.sessionId ?? this.ensureActiveSession();
    if (!q || !sid || !this.sessions[sid] || this.sessionBusy(sid)) return;
    const alsoProjectPaths = opts?.alsoProjectPaths ?? located?.turn.alsoProjectPaths ?? [];

    // Goal composer mode → autonomous multi-pass
    if (this.composerMode === "goal" && !opts?.continuePrior && !retrying) {
      await this.runGoal(q, { alsoProjectPaths, sessionId: sid });
      return;
    }

    if (!retrying) this.input = "";
    app.openAgent();
    this.inspectorOpen = false;
    this.ingestSuggestions = [];
    this.touchUiForSession(sid, { viewMode: "mission" });

    // Same-chat follow-ups always carry prior research + session memory on the server
    const thread = this.getThreadForSession(sid);
    const hasPriorResearch = thread.some(
      (t) => t.kind === "research" && t.status === "done" && t.result,
    );
    const usePrior =
      !!opts?.continuePrior ||
      hasPriorResearch ||
      /^(continue|follow up|deepen|expand|based on (the )?(previous|last|my library and prior))/i.test(
        q,
      );
    const priorContext = usePrior ? this.buildPriorContext(sid) : undefined;
    const projectPath = this.projectPathForSession(sid);

    if (!opts?.skipUserTurn && !retrying) {
      const userTurn: AssistantTurn = { id: newId(), kind: "user", content: q };
      this.appendTurn(userTurn, sid);
    }

    const turnId = located?.turn.id ?? newId();
    this.touchUiForSession(sid, {
      focusedTurnId: turnId,
      activeResearchTurnId: turnId,
      selectedAgentNode: "planner",
    });
    const useReview = this.planReviewEnabled && !opts?.skipPlanReview && !retrying;
    const scope = located?.turn.retrievalScope ?? this.retrievalScope;

    if (located) {
      this.resetResearchTurnForRetry(turnId, { ...located.turn, runMode: "studio" });
    } else {
      this.appendTurn(
        {
          id: turnId,
          kind: "research",
          query: q,
          status: useReview ? "awaiting_plan" : "running",
          progressStep: "planning",
          progressDetail: useReview
            ? "Planner generating plan for review…"
            : "Starting multi-agent workflow…",
          completedSteps: [],
          showAdvanced: false,
          runMode: "studio",
          agentStatuses: {
            ...emptyAgentStatuses(),
            planner: "running",
          },
          activityLog: [
            {
              id: newId(),
              time: formatLogTime(),
              agent: "system",
              message: useReview
                ? `Plan review started · scope ${scope}`
                : `Mission started · scope ${scope}`,
              tone: "live",
            },
          ],
          liveCritiqueHistory: [],
          looping: false,
          alsoProjectPaths,
        },
        sid,
      );
    }

    const started = this.beginJob(sid, "research", {
      turnId,
      timeoutMs: RESEARCH_TIMEOUT_MS,
    });
    if ("error" in started) {
      this.updateResearchTurn(turnId, { status: "error", error: RESEARCH_CAP_MESSAGE });
      this.pushActivity(turnId, "system", RESEARCH_CAP_MESSAGE, "error");
      this.persist();
      return;
    }

    try {
      if (useReview) {
        const planRes = await api.planResearch(q, {
          priorContext,
          signal: this.abortFor(sid)!,
          retrievalScope: scope,
          projectPath,
          sessionId: sid,
          alsoProjectPaths,
        });
        this.updateResearchTurn(turnId, {
          status: "awaiting_plan",
          runId: planRes.run_id,
          planExpiresAt: planRes.expires_at,
          livePlan: planRes.plan,
          liveQueries: planRes.retrieval_queries,
          progressDetail: "Review plan, then approve to execute",
          retrievalScope: (planRes.retrieval_scope as RetrievalScope) || scope,
          agentStatuses: {
            ...emptyAgentStatuses(),
            planner: "waiting_review",
          },
        });
        this.pushActivity(turnId, "Planner", "Plan ready — awaiting approval", "success");
        this.endJob(sid, started.abort);
        this.persist();
        return;
      }

      let result: ResearchResult;
      try {
        result = await api.researchStream(
          q,
          (ev) => this.handleStreamEvent(turnId, ev),
          this.abortFor(sid)!,
          priorContext,
          scope,
          projectPath,
          sid,
          alsoProjectPaths,
        );
      } catch (streamErr) {
        if (streamErr instanceof Error && streamErr.name === "AbortError") throw streamErr;
        this.updateResearchTurn(turnId, {
          progressDetail: "Running multi-agent research (non-stream mode)…",
        });
        this.pushActivity(turnId, "system", "Fallback to non-stream research", "warning");
        result = await api.research(
          q,
          this.abortFor(sid)!,
          priorContext,
          scope,
          projectPath,
          sid,
          alsoProjectPaths,
        );
      }

      await this.finalizeResearchResult(turnId, result);
    } catch (e) {
      const message = this.researchErrorMessage(e, sid);
      this.updateResearchTurn(turnId, {
        status: "error",
        error: message,
      });
      this.pushActivity(turnId, "system", message, "error");
      this.persist();
    } finally {
      const t = this.getThreadForSession(sid).find(
        (x): x is Extract<AssistantTurn, { kind: "research" }> =>
          x.id === turnId && x.kind === "research",
      );
      if (t?.status !== "awaiting_plan") {
        this.endJob(sid, started.abort);
        if (this.activeResearchTurnId === turnId) {
          this.activeResearchTurnId = this.jobs[this.activeSessionId ?? ""]?.turnId ?? null;
        }
        this.persist();
      }
    }
  }

  async approvePlan(
    turnId: string,
    edits: { plan: string; retrieval_queries: string[] },
  ): Promise<void> {
    // Prefer active session; fall back to session that owns the turn
    let sid = this.activeSessionId;
    let turn = this.getThreadForSession(sid).find(
      (t): t is Extract<AssistantTurn, { kind: "research" }> =>
        t.id === turnId && t.kind === "research",
    );
    if (!turn) {
      for (const s of Object.values(this.sessions)) {
        const found = s.turns.find(
          (t): t is Extract<AssistantTurn, { kind: "research" }> =>
            t.id === turnId && t.kind === "research",
        );
        if (found) {
          sid = s.id;
          turn = found;
          break;
        }
      }
    }
    if (!turn || turn.status !== "awaiting_plan" || !turn.runId || !sid) return;
    if (this.sessionBusy(sid)) return;

    this.activeResearchTurnId = turnId;
    const started = this.beginJob(sid, "research", {
      turnId,
      timeoutMs: RESEARCH_TIMEOUT_MS,
    });
    if ("error" in started) {
      this.updateResearchTurn(turnId, { status: "error", error: RESEARCH_CAP_MESSAGE });
      return;
    }

    this.updateResearchTurn(turnId, {
      status: "running",
      livePlan: edits.plan,
      liveQueries: edits.retrieval_queries,
      progressStep: "searching",
      progressDetail: "Executing approved plan…",
      agentStatuses: {
        ...emptyAgentStatuses(),
        planner: "done",
        retriever: "running",
      },
    });
    this.pushActivity(turnId, "system", "Plan approved — executing", "live");

    try {
      const result = await api.executeResearchStream(
        {
          run_id: turn.runId,
          query: turn.query,
          plan: edits.plan,
          retrieval_queries: edits.retrieval_queries,
          retrieval_scope: turn.retrievalScope ?? this.retrievalScope,
          project_path: this.activeProjectPath(),
          session_id: sid ?? this.activeSessionId,
          also_project_paths: turn.alsoProjectPaths ?? [],
        },
        (ev) => this.handleStreamEvent(turnId, ev),
        this.abortFor(sid)!,
      );
      await this.finalizeResearchResult(turnId, result);
    } catch (e) {
      const message = this.researchErrorMessage(e, sid);
      this.updateResearchTurn(turnId, { status: "error", error: message });
      this.pushActivity(turnId, "system", message, "error");
      this.persist();
    } finally {
      this.endJob(sid, started.abort);
      if (this.activeResearchTurnId === turnId) {
        this.activeResearchTurnId = this.jobs[this.activeSessionId ?? ""]?.turnId ?? null;
      }
      this.persist();
    }
  }

  async regeneratePlan(turnId: string): Promise<void> {
    let sid = this.activeSessionId;
    let turn = this.getThreadForSession(sid).find(
      (t): t is Extract<AssistantTurn, { kind: "research" }> =>
        t.id === turnId && t.kind === "research",
    );
    if (!turn) {
      for (const s of Object.values(this.sessions)) {
        const found = s.turns.find(
          (t): t is Extract<AssistantTurn, { kind: "research" }> =>
            t.id === turnId && t.kind === "research",
        );
        if (found) {
          sid = s.id;
          turn = found;
          break;
        }
      }
    }
    if (!turn || this.sessionBusy(sid) || !sid) return;
    const started = this.beginJob(sid, "research", { turnId });
    if ("error" in started) return;
    this.updateResearchTurn(turnId, {
      progressDetail: "Regenerating plan…",
      agentStatuses: { ...emptyAgentStatuses(), planner: "running" },
    });
    this.pushActivity(turnId, "Planner", "Regenerating plan", "live");

    try {
      const planRes = await api.planResearch(turn.query, {
        priorContext: turn.priorContext,
        replaceRunId: turn.runId,
        signal: this.abortFor(sid)!,
        retrievalScope: turn.retrievalScope ?? this.retrievalScope,
        projectPath: this.activeProjectPath(),
        sessionId: sid,
        alsoProjectPaths: turn.alsoProjectPaths,
      });
      this.updateResearchTurn(turnId, {
        status: "awaiting_plan",
        runId: planRes.run_id,
        planExpiresAt: planRes.expires_at,
        livePlan: planRes.plan,
        liveQueries: planRes.retrieval_queries,
        progressDetail: "Review regenerated plan",
        agentStatuses: { ...emptyAgentStatuses(), planner: "waiting_review" },
      });
      this.pushActivity(turnId, "Planner", "New plan ready", "success");
      this.persist();
    } catch (e) {
      const message = this.researchErrorMessage(e, sid);
      this.updateResearchTurn(turnId, { status: "error", error: message });
      this.pushActivity(turnId, "system", message, "error");
      this.persist();
    } finally {
      this.endJob(sid, started.abort);
    }
  }

  async cancelPlanReview(turnId: string): Promise<void> {
    let sid = this.activeSessionId;
    let turn = this.getThreadForSession(sid).find(
      (t): t is Extract<AssistantTurn, { kind: "research" }> =>
        t.id === turnId && t.kind === "research",
    );
    if (!turn) {
      for (const s of Object.values(this.sessions)) {
        const found = s.turns.find(
          (t): t is Extract<AssistantTurn, { kind: "research" }> =>
            t.id === turnId && t.kind === "research",
        );
        if (found) {
          sid = s.id;
          turn = found;
          break;
        }
      }
    }
    if (!turn?.runId) {
      this.updateResearchTurn(turnId, {
        status: "error",
        error: "Plan review cancelled",
      });
      this.persist();
        return;
    }
    try {
      await api.cancelResearchRun(turn.runId);
    } catch {
      /* ignore */
    }
    this.updateResearchTurn(turnId, {
      status: "error",
      error: "Plan review cancelled",
    });
    this.pushActivity(turnId, "system", "Plan review cancelled", "warning");
    this.persist();
  }

  toggleAdvanced(_notePath: string | null, turnId: string): void {
    const sid = this.activeSessionId;
    const turn = this.getThreadForSession(sid).find((t) => t.id === turnId);
    if (turn?.kind === "research") {
        this.updateResearchTurn(turnId, { showAdvanced: !turn.showAdvanced });
        this.persist();
    }
  }
}

export const assistant = new AssistantStore();
