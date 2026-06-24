import { api, type ResearchResult } from "$lib/api";

export interface ResearchRunState {
  result: ResearchResult | null;
  error: string;
}

/** Execute research via the sidecar /api/research endpoint. */
export async function runResearchQuery(query: string): Promise<ResearchRunState> {
  const trimmed = query.trim();
  if (!trimmed) {
    return { result: null, error: "" };
  }

  try {
    const result = await api.research(trimmed);
    return { result, error: "" };
  } catch (e) {
    return {
      result: null,
      error: e instanceof Error ? e.message : "Research failed",
    };
  }
}