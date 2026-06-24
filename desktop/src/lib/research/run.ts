import { api, type ResearchResult } from "$lib/api";

export interface ResearchRunState {
  loading: boolean;
  result: ResearchResult | null;
  error: string;
}

/** Execute research via the sidecar /api/research endpoint. */
export async function runResearchQuery(query: string): Promise<ResearchRunState> {
  const trimmed = query.trim();
  if (!trimmed) {
    return { loading: false, result: null, error: "" };
  }

  try {
    const result = await api.research(trimmed);
    return { loading: false, result, error: "" };
  } catch (e) {
    return {
      loading: false,
      result: null,
      error: e instanceof Error ? e.message : "Research failed",
    };
  }
}