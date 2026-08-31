import { invoke } from "@tauri-apps/api/core";

const DEFAULT_URL = "http://127.0.0.1:8765";

let cachedBaseUrl: string | null = null;

export async function getBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return cachedBaseUrl;
  try {
    cachedBaseUrl = await invoke<string>("get_sidecar_url");
  } catch {
    // Browser / vite-only: Tauri invoke unavailable
    cachedBaseUrl = DEFAULT_URL;
  }
  return cachedBaseUrl ?? DEFAULT_URL;
}

/** Clear cached URL after sidecar restart. */
export function resetSidecarUrlCache(): void {
  cachedBaseUrl = null;
}

export async function waitForSidecar(maxAttempts = 30): Promise<boolean> {
  const base = await getBaseUrl();
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${base}/health`, { signal: AbortSignal.timeout(2000) });
      if (res.ok) return true;
    } catch {
      /* sidecar still starting or hung */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

type FastApiDetail =
  | string
  | { msg?: string; loc?: (string | number)[] }[];

function formatApiDetail(detail: FastApiDetail | undefined, status: number): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d) => {
        const loc = (d.loc ?? []).filter((x) => x !== "body" && x !== "query" && x !== "path");
        const field = loc.map(String).join(".");
        const msg = d.msg || "Invalid";
        return field ? `${field}: ${msg}` : msg;
      })
      .join("; ");
  }
  return `Request failed: ${status}`;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const base = await getBaseUrl();
  const method = (options?.method ?? "GET").toUpperCase();
  const headers = new Headers(options?.headers);
  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  // Forward Better Auth session to Cloud Watch routes (no sidecar .env token).
  if (path.startsWith("/api/cloud-watch/") && !headers.has("Authorization")) {
    try {
      const { getSessionToken } = await import("$lib/auth/session");
      const token = getSessionToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    } catch {
      /* ignore */
    }
  }
  const res = await fetch(`${base}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: FastApiDetail };
    throw new Error(formatApiDetail(body.detail, res.status));
  }
  return res.json();
}

async function listWatchesRequest(projectPath?: string | null): Promise<WatchListResponse> {
  const q = projectPath ? `?project_path=${encodeURIComponent(projectPath)}` : "";
  return apiFetch<WatchListResponse>(`/api/watches${q}`);
}

export interface Status {
  collection_count: number;
  project_root: string;
  ollama_url: string;
  llm_provider?: string;
  llm_model?: string;
  llm_fast_model?: string;
  embeddings_provider?: string;
  embeddings_model?: string;
  embeddings_ok?: boolean;
  embeddings_error?: string;
  embedding_dims?: number | null;
  reindex_required?: boolean;
  fingerprint?: Record<string, unknown> | null;
}

export interface Source {
  index: number;
  source: string;
  page: number | null;
  excerpt: string;
}

export interface QueryResult {
  question: string;
  answer: string;
  sources: Source[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatContext {
  note_path?: string | null;
  selected_text?: string | null;
  note_excerpt?: string | null;
}

export interface ChatResult {
  question: string;
  answer: string;
  sources: Source[];
  thin_memory?: boolean;
  contested_claims?: {
    id?: string;
    claim?: string;
    origin?: string;
    status?: string;
    slug?: string;
  }[] | null;
}

export type ManagerKind = "ask" | "dispatch" | "meta";
export type ManagerJob =
  | "file"
  | "answer"
  | "research"
  | "refuse"
  | "watch"
  | "retarget"
  | "merge"
  | "split";

export interface ManagerTurn {
  kind: ManagerKind;
  text: string;
  focus: "clarify" | "confirm" | null;
  job: ManagerJob | null;
  instruction: string | null;
  retrieval_scope: "local" | "hybrid" | "web" | null;
  reason: string;
  route_tier?: string;
  confidence?: number;
  refuse_message: string | null;
  matching_claim_count: number;
  topic: string;
  create_topic: string | null;
  retarget_topic?: string;
  merge_source?: string;
  merge_dest?: string;
  also_topics?: string[];
  also_project_paths?: string[];
  new_topic?: string;
  idea?: string;
}

export interface DigestResult {
  saved_path: string;
  content_hash: string;
  idempotent: boolean;
  claims_created: number;
  claims_revised: number;
  claims_dropped: number;
  linked_sources: string[];
  open_questions: string[];
  summary: string;
  claim_slugs?: string[];
}

export interface WatchBriefRow {
  path: string;
  day: string;
  excerpt: string;
}

export interface WatchListItem {
  watch_id: string;
  name: string;
  project_path: string;
  topic: string;
  created: string;
  enabled: boolean;
  complete: boolean;
  has_brief_today: boolean;
}

export interface WatchListResponse {
  watches: WatchListItem[];
  has_memory: boolean;
}

export interface WatchStatus {
  watch_id: string;
  name: string;
  project_path: string;
  topic: string;
  created: string;
  enabled: boolean;
  instruction: string;
  focus: string;
  include: string;
  exclude: string;
  trusted_sources?: string;
  steer_log: string;
  complete: boolean;
  suggested_focus: string;
  has_brief_today: boolean;
  brief_path: string | null;
  latest_brief: string;
  briefs: WatchBriefRow[];
  claim_count: number;
  has_memory: boolean;
}

export type CritiqueSeverity = "info" | "minor" | "major" | "blocking";
export type CritiqueVerdict = "approved" | "revise";

export interface CritiqueIssue {
  code: string;
  severity: CritiqueSeverity;
  message: string;
  citation_indices?: number[];
}

export interface StructuredCritique {
  verdict: CritiqueVerdict;
  summary: string;
  issues: CritiqueIssue[];
  grounding_passed: boolean;
  source: string;
  raw?: string | null;
}

export interface CritiqueHistoryEntry {
  revision_index: number;
  critique: StructuredCritique;
  analysis_char_count?: number;
  analysis_excerpt?: string;
  ts?: string;
}

/** Where agents may search for a research run. */
export type RetrievalScope = "local" | "hybrid" | "web";

export const RETRIEVAL_SCOPE_OPTIONS: {
  value: RetrievalScope;
  label: string;
  hint: string;
}[] = [
  { value: "local", label: "Library", hint: "Local vault only" },
  { value: "hybrid", label: "Library + Web", hint: "Personal + web + arXiv" },
  { value: "web", label: "Web", hint: "External only (no vault)" },
];

export interface ResearchResult {
  query: string;
  plan: string;
  retrieval_queries: string[];
  retrieval_stats: Record<string, number>;
  retrieval_log: string[];
  analysis: string;
  revision_count: number;
  report: string;
  /** Path if auto-saved into the vault */
  saved_path?: string;
  /** Latest free-text critique (analyst contract) */
  critique?: string;
  critique_approved?: boolean;
  critique_structured?: StructuredCritique | null;
  critique_history?: CritiqueHistoryEntry[];
  analysis_history?: {
    revision_index: number;
    analysis_excerpt?: string;
    analysis_char_count?: number;
    ts?: string;
  }[];
  retrieval_scope?: RetrievalScope | string;
  /** 0–1 heuristic quality signal */
  confidence?: number | null;
  confidence_reasons?: string[];
  open_questions?: string[];
  learning_path?: string | null;
  report_path?: string | null;
  citation_issues?: string[];
  memory_recalled_count?: number | null;
  /** False when lookup was answered but not filed into this topic. */
  memory_written?: boolean | null;
  memory_detail?: string | null;
  claim_count?: number | null;
  claim_slugs?: string[] | null;
  claims_revised?: number | null;
  contested_claims?: {
    id?: string;
    claim?: string;
    origin?: string;
    status?: string;
    slug?: string;
  }[] | null;
  goal?: string | null;
  goal_status?: string | null;
  goal_stop_reason?: string | null;
  brief_path?: string | null;
  slow_day?: boolean | null;
  passes?: {
    pass: number;
    query?: string;
    confidence?: number;
    open_questions?: string[];
    learning_path?: string | null;
    report_path?: string | null;
    revision_count?: number;
  }[];
  pass_count?: number | null;
  brief_path?: string | null;
  slow_day?: boolean | null;
}

export type AgentStreamStatus =
  | "pending"
  | "running"
  | "done"
  | "iterating"
  | "error"
  | "waiting_review";

/** Flat dual-compat SSE events — ignore unknown types. */
export type ResearchStreamEvent =
  | {
      type: "stage";
      node: string;
      step: string;
      detail?: string;
      label?: string;
    }
  | {
      type: "agent_status";
      node: string;
      status: AgentStreamStatus;
      step?: string;
      label?: string;
      detail?: string;
    }
  | {
      type: "plan";
      plan: string;
      retrieval_queries?: string[];
    }
  | {
      type: "artifact";
      kind: string;
      retrieval_stats?: Record<string, number>;
      retrieval_log?: string[];
      analysis_excerpt?: string;
      analysis_char_count?: number;
    }
  | {
      type: "critique";
      critique?: string;
      critique_approved?: boolean;
      revision_count?: number;
      critique_structured?: StructuredCritique | null;
      history_entry?: CritiqueHistoryEntry | null;
    }
  | {
      type: "memory";
      phase?: "recalled" | "written" | string;
      recalled_count?: number;
      sources?: string[];
      learning_path?: string | null;
      report_path?: string | null;
      confidence?: number;
      detail?: string;
    }
  | {
      type: "goal_pass";
      pass?: number;
      max_passes?: number;
      reason?: string;
      query?: string;
      detail?: string;
    }
  | {
      type: "goal_status";
      status?: string;
      stop_reason?: string;
      pass_count?: number;
      max_passes?: number;
      confidence?: number;
      detail?: string;
    }
  | { type: "watch_brief"; brief_path?: string; slow_day?: boolean; detail?: string }
  | { type: "result"; result: ResearchResult }
  | { type: "done" }
  | { type: "error"; message: string };

export interface IngestResult {
  ingested_chunks: number;
  collection_total: number;
  path: string;
  suggestions?: string[];
  reset?: boolean;
}

export interface Settings {
  values: Record<string, string>;
  tavily_configured: boolean;
  notion_configured?: boolean;
  groq_configured: boolean;
  /** True when current provider can run (ollama always; cloud needs a key). */
  llm_configured?: boolean;
  /** True when Nous-included NVIDIA access is active (no user key). */
  llm_bundled?: boolean;
  llm_provider: string;
  /** Which providers have credentials stored (BYOK connect status). */
  connected_providers?: Record<string, boolean>;
}

export interface VaultSearchResult {
  source: string;
  excerpt: string;
  distance: number;
  page: number | null;
}

export interface VaultSearchResponse {
  query: string;
  results: VaultSearchResult[];
}

export interface ReviewGoalRun {
  goal: string;
  kind?: string;
  source?: string;
  confidence?: number;
  open_questions?: string[];
  learning_path?: string | null;
  report_path?: string | null;
  error?: string;
}

export interface ReviewStatus {
  enabled: boolean;
  running: boolean;
  last_run_date: string | null;
  last_run_status: string;
  last_run_started_at?: string | null;
  last_run_finished_at?: string | null;
  last_run_reason?: string | null;
  goals_run: ReviewGoalRun[];
  new_files: string[];
  digest_path: string | null;
  skipped_reason?: string | null;
  error?: string | null;
  last_watch_error?: string | null;
  next_eligible_date?: string | null;
}

export interface DailyDigest {
  date: string;
  path: string;
  content: string;
  body: string;
  learnings: number;
  goals: number;
  summary: string;
}

export interface DigestTodayResponse {
  date: string | null;
  digest: DailyDigest | null;
  /** Most recent prior digest when today's is missing */
  previous_digest?: DailyDigest | null;
  review: ReviewStatus;
}

export interface DigestListItem {
  date: string;
  path: string;
  learnings: number;
  goals: number;
  summary: string;
}

export interface ReviewPlanPreview {
  goals: { goal: string; kind: string; source?: string }[];
  new_files: string[];
  open_questions: { question: string; from_query?: string }[];
  skip_reason: string | null;
  watch_error?: string | null;
}

export interface ResearchPlanResponse {
  run_id: string;
  query: string;
  composed_query: string;
  plan: string;
  retrieval_queries: string[];
  status: "pending_approval";
  expires_at: string;
  retrieval_scope?: RetrievalScope | string;
}

async function readResearchSse(
  res: Response,
  onEvent: (ev: ResearchStreamEvent) => void,
): Promise<ResearchResult> {
  if (!res.body) throw new Error("No response body from research stream");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: ResearchResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        const raw = JSON.parse(line.slice(6)) as { type?: string };
        if (!raw || typeof raw.type !== "string") continue;
        const known = new Set([
          "stage",
          "agent_status",
          "plan",
          "artifact",
          "critique",
          "memory",
          "goal_pass",
          "goal_status",
          "watch_brief",
          "result",
          "done",
          "error",
        ]);
        if (!known.has(raw.type)) continue;
        const ev = raw as ResearchStreamEvent;
        onEvent(ev);
        if (ev.type === "result") finalResult = ev.result;
        if (ev.type === "error") throw new Error(ev.message);
      } catch (e) {
        if (e instanceof SyntaxError) continue;
        throw e;
      }
    }
  }

  if (!finalResult) throw new Error("Research stream ended without a result");
  return finalResult;
}

function streamErrorMessage(res: Response, body: unknown): string {
  const detail = (body as { detail?: string | { msg: string }[] })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  return `Request failed: ${res.status}`;
}

export interface SidecarHealth {
  status: string;
  watches_api?: number;
}

/** Sidecar Watch HTTP surface the desktop expects (GET list + POST create/update/move/delete). */
export const WATCHES_API_VERSION = 3;

export const api = {
  health: () => apiFetch<SidecarHealth>("/health"),
  status: () => apiFetch<Status>("/api/status"),
  query: (question: string, top_k = 5) =>
    apiFetch<QueryResult>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, top_k }),
    }),
  chat: (
    messages: ChatMessage[],
    context?: ChatContext,
    top_k = 5,
    opts?: { projectPath?: string | null; sessionId?: string | null; alsoProjectPaths?: string[] },
  ) =>
    apiFetch<ChatResult>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        messages,
        context: context ?? null,
        top_k,
        project_path: opts?.projectPath ?? null,
        session_id: opts?.sessionId ?? null,
        also_project_paths: opts?.alsoProjectPaths ?? [],
      }),
    }),
  managerTurn: (body: {
    message: string;
    projectPath?: string | null;
    sessionId?: string | null;
    hasAttachments?: boolean;
    clarifyCount?: number;
    history?: { role: string; content: string }[];
    topics?: { name: string; path: string }[];
    forcedJob?: "answer" | "research" | "file" | "watch" | null;
  }) =>
    apiFetch<ManagerTurn>("/api/manager/turn", {
      method: "POST",
      body: JSON.stringify({
        message: body.message,
        project_path: body.projectPath ?? null,
        session_id: body.sessionId ?? null,
        has_attachments: body.hasAttachments ?? false,
        clarify_count: body.clarifyCount ?? 0,
        history: body.history ?? [],
        topics: body.topics ?? [],
        forced_job: body.forcedJob ?? null,
      }),
    }),
  digest: (body: {
    text?: string | null;
    title?: string | null;
    path?: string | null;
    paths?: string[];
    projectPath?: string | null;
    sessionId?: string | null;
  }, signal?: AbortSignal) =>
    apiFetch<DigestResult>("/api/digest", {
      method: "POST",
      body: JSON.stringify({
        text: body.text ?? null,
        title: body.title ?? null,
        path: body.path ?? null,
        paths: body.paths ?? null,
        project_path: body.projectPath ?? null,
        session_id: body.sessionId ?? null,
      }),
      signal,
    }),
  mergeMemory: (body: { sourceProjectPath: string; destProjectPath: string }) =>
    apiFetch<{
      copied: number;
      skipped: number;
      source_name: string;
      dest_name: string;
    }>("/api/memory/merge", {
      method: "POST",
      body: JSON.stringify({
        source_project_path: body.sourceProjectPath,
        dest_project_path: body.destProjectPath,
        ingest: true,
      }),
    }),
  listWatches: listWatchesRequest,
  /** Vault-wide list; if the sidecar requires project_path, fetch each topic. */
  listAllWatches: async (projectPaths: string[]) => {
    try {
      return await listWatchesRequest();
    } catch (e) {
      if (!projectPaths.length) throw e;
      const parts = await Promise.all(
        projectPaths.map(async (p) => {
          try {
            return (await listWatchesRequest(p)).watches;
          } catch {
            return [] as WatchListItem[];
          }
        }),
      );
      const watches = parts.flat();
      if (watches.length === 0) throw e;
      return { watches, has_memory: false } satisfies WatchListResponse;
    }
  },
  getWatch: async (projectPath: string, watchId?: string | null) => {
    const id = watchId || "legacy";
    const q = `project_path=${encodeURIComponent(projectPath)}`;
    try {
      return await apiFetch<WatchStatus>(`/api/watches/${encodeURIComponent(id)}?${q}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (!/\b(404|405)\b/.test(msg) && !/not found/i.test(msg)) throw e;
      return apiFetch<WatchStatus>(
        `/api/watches?${new URLSearchParams({ project_path: projectPath, watch_id: id }).toString()}`,
      );
    }
  },
  promoteWatch: (projectPath: string, name?: string | null) =>
    apiFetch<WatchStatus>("/api/watches/promote", {
      method: "POST",
      body: JSON.stringify({
        project_path: projectPath,
        name: name ?? null,
      }),
    }),
    createWatch: (
    projectPath: string,
    body?: {
      name?: string;
      focus?: string | null;
      include?: string | null;
      enabled?: boolean;
      cadence?: string | null;
      hour?: number | null;
    },
  ) =>
    apiFetch<WatchStatus>("/api/watches", {
      method: "POST",
      body: JSON.stringify({
        project_path: projectPath,
        name: body?.name ?? "Untitled",
        focus: body?.focus ?? null,
        include: body?.include ?? null,
        enabled: body?.enabled ?? false,
        cadence: body?.cadence ?? null,
        hour: body?.hour ?? null,
      }),
    }),
    moveWatch: (projectPath: string, destProjectPath: string, watchId?: string | null) =>
    apiFetch<WatchStatus>("/api/watches/move", {
      method: "POST",
      body: JSON.stringify({
        project_path: projectPath,
        dest_project_path: destProjectPath,
        watch_id: watchId || "legacy",
      }),
    }),
  deleteWatch: (projectPath: string, watchId?: string | null) =>
    apiFetch<{ ok: boolean }>("/api/watches/delete", {
      method: "POST",
      body: JSON.stringify({
        project_path: projectPath,
        watch_id: watchId || "legacy",
      }),
    }),
  updateWatch: async (
    projectPath: string,
    body: {
      watchId?: string | null;
      name?: string | null;
      focus?: string | null;
      include?: string | null;
      exclude?: string | null;
      trustedSources?: string | null;
      enabled?: boolean | null;
      cadence?: string | null;
      hour?: number | null;
    },
  ) => {
    const payload = {
      project_path: projectPath,
      watch_id: body.watchId || "legacy",
      name: body.name ?? null,
      focus: body.focus ?? null,
      include: body.include ?? null,
      exclude: body.exclude ?? null,
      trusted_sources: body.trustedSources ?? null,
      enabled: body.enabled ?? null,
      cadence: body.cadence ?? null,
      hour: body.hour ?? null,
    };
    try {
      return await apiFetch<WatchStatus>("/api/watches/update", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      if (!/\b(404|405)\b/.test(msg) && !/not found/i.test(msg)) throw e;
      try {
        return await apiFetch<WatchStatus>("/api/watches", {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } catch {
        throw new Error(
          "Could not save. Restart the app so Scheduled Research can reach the sidecar.",
        );
      }
    }
  },
  watchSteer: (projectPath: string, note: string, watchId?: string | null) =>
    apiFetch<{ ok: boolean; path: string }>("/api/watches/steer", {
      method: "POST",
      body: JSON.stringify({
        project_path: projectPath,
        watch_id: watchId || "legacy",
        note,
      }),
    }),
  watchStream: async (
    projectPath: string,
    onEvent: (ev: ResearchStreamEvent) => void,
    signal?: AbortSignal,
    opts?: {
      force?: boolean;
      sessionId?: string | null;
      maxPasses?: number;
      watchId?: string | null;
    },
  ): Promise<ResearchResult> => {
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/watches/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        project_path: projectPath,
        watch_id: opts?.watchId || "legacy",
        force: opts?.force ?? false,
        session_id: opts?.sessionId ?? null,
        ...(opts?.maxPasses != null ? { max_passes: opts.maxPasses } : {}),
      }),
      signal,
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(streamErrorMessage(res, errBody));
    }
    return readResearchSse(res, onEvent);
  },
  research: (
    query: string,
    signal?: AbortSignal,
    priorContext?: string,
    retrievalScope: RetrievalScope = "hybrid",
    projectPath?: string | null,
    sessionId?: string | null,
    alsoProjectPaths?: string[] | null,
  ) =>
    apiFetch<ResearchResult>("/api/research", {
      method: "POST",
      body: JSON.stringify({
        query,
        prior_context: priorContext ?? null,
        retrieval_scope: retrievalScope,
        project_path: projectPath ?? null,
        session_id: sessionId ?? null,
        also_project_paths: alsoProjectPaths ?? [],
      }),
      signal,
    }),

  /** Plan-only HITL (JSON). Product path for plan review. */
  planResearch: (
    query: string,
    opts?: {
      priorContext?: string;
      replaceRunId?: string;
      signal?: AbortSignal;
      retrievalScope?: RetrievalScope;
      projectPath?: string | null;
      sessionId?: string | null;
      alsoProjectPaths?: string[];
    },
  ) =>
    apiFetch<ResearchPlanResponse>("/api/research/plan", {
      method: "POST",
      body: JSON.stringify({
        query,
        prior_context: opts?.priorContext ?? null,
        replace_run_id: opts?.replaceRunId ?? null,
        retrieval_scope: opts?.retrievalScope ?? "hybrid",
        project_path: opts?.projectPath ?? null,
        session_id: opts?.sessionId ?? null,
        also_project_paths: opts?.alsoProjectPaths ?? [],
      }),
      signal: opts?.signal,
    }),

  /** Execute approved plan via SSE (requires final result). */
  executeResearchStream: async (
    body: {
      run_id: string;
      query: string;
      plan: string;
      retrieval_queries: string[];
      retrieval_scope?: RetrievalScope;
      project_path?: string | null;
      session_id?: string | null;
      also_project_paths?: string[];
    },
    onEvent: (ev: ResearchStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<ResearchResult> => {
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/research/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(streamErrorMessage(res, errBody));
    }
    return readResearchSse(res, onEvent);
  },

  cancelResearchRun: (runId: string) =>
    apiFetch<{ ok: boolean }>(`/api/research/runs/${runId}`, { method: "DELETE" }),

  /**
   * Autonomous multi-pass goal stream (no plan review).
   * Throws STREAM_UNAVAILABLE if the sidecar is too old (missing /api/goals/stream).
   */
  goalStream: async (
    goal: string,
    onEvent: (ev: ResearchStreamEvent) => void,
    signal?: AbortSignal,
    opts?: {
      retrievalScope?: RetrievalScope;
      projectPath?: string | null;
      sessionId?: string | null;
      maxPasses?: number;
      minConfidence?: number;
      alsoProjectPaths?: string[];
    },
  ): Promise<ResearchResult> => {
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/goals/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        goal,
        retrieval_scope: opts?.retrievalScope ?? "hybrid",
        project_path: opts?.projectPath ?? null,
        session_id: opts?.sessionId ?? null,
        max_passes: opts?.maxPasses,
        min_confidence: opts?.minConfidence ?? 0.65,
        also_project_paths: opts?.alsoProjectPaths ?? [],
      }),
      signal,
    });
    if (!res.ok) {
      if (res.status === 404) {
        throw new Error("STREAM_UNAVAILABLE");
      }
      const errBody = await res.json().catch(() => ({}));
      throw new Error(streamErrorMessage(res, errBody));
    }
    return readResearchSse(res, onEvent);
  },

  /**
   * Full auto multi-agent SSE. Do not use for plan_mode=review.
   */
  researchStream: async (
    query: string,
    onEvent: (ev: ResearchStreamEvent) => void,
    signal?: AbortSignal,
    priorContext?: string,
    retrievalScope: RetrievalScope = "hybrid",
    projectPath?: string | null,
    sessionId?: string | null,
    alsoProjectPaths?: string[] | null,
  ): Promise<ResearchResult> => {
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/research/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        query,
        prior_context: priorContext ?? null,
        retrieval_scope: retrievalScope,
        project_path: projectPath ?? null,
        session_id: sessionId ?? null,
        also_project_paths: alsoProjectPaths ?? [],
      }),
      signal,
    });
    if (!res.ok) {
      if (res.status === 404) {
        throw new Error("STREAM_UNAVAILABLE");
      }
      const errBody = await res.json().catch(() => ({}));
      throw new Error(streamErrorMessage(res, errBody));
    }
    return readResearchSse(res, onEvent);
  },

  ingest: (path: string, opts?: { reset?: boolean }) =>
    apiFetch<IngestResult>("/api/ingest", {
      method: "POST",
      body: JSON.stringify({ path, reset: !!opts?.reset }),
    }),
  ingestFile: (path: string) =>
    apiFetch<IngestResult>("/api/ingest/file", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
  getSettings: () => apiFetch<Settings>("/api/settings"),
  /** Gemini Flash-Lite chat rename. Returns null title when unconfigured / failed. */
  suggestSessionTitle: (message: string) =>
    apiFetch<{ title: string | null; configured: boolean; model: string }>(
      "/api/session-title",
      {
        method: "POST",
        body: JSON.stringify({ message }),
      },
    ),
  mcpStatus: () =>
    apiFetch<{
      enabled: boolean;
      configured: boolean;
      ok: boolean;
      error: string;
    }>("/api/mcp/status"),
  cloudWatchStatus: () =>
    apiFetch<{
      available?: boolean;
      configured: boolean;
      signed_in?: boolean;
      url: string;
      user?: { email?: string; has_api_key?: boolean; llm_provider?: string } | null;
    }>("/api/cloud-watch/status"),
  cloudWatchSaveLlm: (body: {
    llm_provider: string;
    llm_api_key: string;
    llm_model?: string;
  }) =>
    apiFetch<{ ok: boolean; user?: Record<string, unknown> }>("/api/cloud-watch/llm", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  /** Push Settings → Models key to Cloud Watch (same key as Research). */
  cloudWatchSyncLlm: () =>
    apiFetch<{ ok: boolean; user?: Record<string, unknown> }>("/api/cloud-watch/llm/sync", {
      method: "POST",
    }),
  cloudWatchSync: (projectPath: string, watchId?: string | null) =>
    apiFetch<{ ok: boolean; skipped?: boolean; reason?: string; watch?: Record<string, unknown> }>(
      "/api/cloud-watch/sync",
      {
        method: "POST",
        body: JSON.stringify({
          project_path: projectPath,
          watch_id: watchId || "legacy",
        }),
      },
    ),
  cloudWatchPull: () =>
    apiFetch<{
      ok: boolean;
      skipped?: boolean;
      reason?: string;
      count: number;
      written: { path: string; watch_id: string; day: string }[];
      errors?: string[];
    }>("/api/cloud-watch/pull", { method: "POST" }),
  cloudWatchSyncAll: () =>
    apiFetch<{
      ok: boolean;
      skipped?: boolean;
      reason?: string;
      count: number;
      synced: string[];
      errors?: string[];
    }>("/api/cloud-watch/sync-all", { method: "POST" }),
  cloudWatchDelegate: (delegated: boolean) =>
    apiFetch<{ ok: boolean; delegated: boolean }>("/api/cloud-watch/delegate", {
      method: "POST",
      body: JSON.stringify({ delegated }),
    }),
  updateSettings: (values: Record<string, string>) =>
    apiFetch<{ updated: string[]; values: Record<string, string> }>("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ values }),
    }),
  restartSidecar: () => invoke<string>("restart_sidecar"),
  vaultSearch: (query: string, top_k = 8) =>
    apiFetch<VaultSearchResponse>("/api/vault/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k }),
    }),
  vaultRelated: (text: string, top_k = 5) =>
    apiFetch<VaultSearchResponse>("/api/vault/related", {
      method: "POST",
      body: JSON.stringify({ text, top_k }),
    }),
  digestToday: () => apiFetch<DigestTodayResponse>("/api/digest/today"),
  listDigests: (limit = 30) =>
    apiFetch<{ digests: DigestListItem[] }>(`/api/digests?limit=${limit}`),
  reviewStatus: () => apiFetch<ReviewStatus>("/api/review/status"),
  reviewPlan: () => apiFetch<ReviewPlanPreview>("/api/review/plan"),
  reviewRunNow: (force = true) =>
    apiFetch<ReviewStatus>(`/api/review/run-now?force=${force}`, { method: "POST" }),
  agentDefaults: () =>
    apiFetch<{
      daily_review_enabled?: boolean;
      daily_review_hour?: number;
      daily_review_max_goals?: number;
      auto_memory?: boolean;
      auto_recall?: boolean;
      max_goal_passes?: number;
      watch_max_passes?: number;
      min_goal_confidence?: number;
      enable_web_search?: boolean;
      enable_arxiv?: boolean;
    }>("/api/agent/defaults"),
};