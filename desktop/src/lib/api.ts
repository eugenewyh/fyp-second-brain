import { invoke } from "@tauri-apps/api/core";

const DEFAULT_URL = "http://127.0.0.1:8765";

let cachedBaseUrl: string | null = null;

export async function getBaseUrl(): Promise<string> {
  if (!cachedBaseUrl) {
    cachedBaseUrl = await invoke<string>("get_sidecar_url");
  }
  return cachedBaseUrl;
}

export async function waitForSidecar(maxAttempts = 30): Promise<boolean> {
  const base = await getBaseUrl();
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(`${base}/health`);
      if (res.ok) return true;
    } catch {
      /* sidecar still starting */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const base = await getBaseUrl();
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string | { msg: string }[] };
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(", ")
          : `Request failed: ${res.status}`;
    throw new Error(message);
  }
  return res.json();
}

export interface Status {
  collection_count: number;
  project_root: string;
  ollama_url: string;
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
}

export interface ResearchResult {
  query: string;
  plan: string;
  retrieval_queries: string[];
  retrieval_stats: Record<string, number>;
  retrieval_log: string[];
  analysis: string;
  revision_count: number;
  report: string;
}

export interface Settings {
  values: Record<string, string>;
  tavily_configured: boolean;
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

export const api = {
  status: () => apiFetch<Status>("/api/status"),
  query: (question: string, top_k = 5) =>
    apiFetch<QueryResult>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, top_k }),
    }),
  chat: (messages: ChatMessage[], context?: ChatContext, top_k = 5) =>
    apiFetch<ChatResult>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ messages, context: context ?? null, top_k }),
    }),
  research: (query: string) =>
    apiFetch<ResearchResult>("/api/research", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  ingest: (path: string) =>
    apiFetch<{ ingested_chunks: number; collection_total: number; path: string }>(
      "/api/ingest",
      { method: "POST", body: JSON.stringify({ path }) },
    ),
  ingestFile: (path: string) =>
    apiFetch<{ ingested_chunks: number; collection_total: number; path: string }>(
      "/api/ingest/file",
      { method: "POST", body: JSON.stringify({ path }) },
    ),
  getSettings: () => apiFetch<Settings>("/api/settings"),
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
};