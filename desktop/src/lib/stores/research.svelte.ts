import { api, type QueryResult, type ResearchResult } from "$lib/api";
import { connection } from "$lib/stores/connection.svelte";
import { tabs } from "$lib/stores/tabs.svelte";

class ResearchStore {
  query = $state("");
  loading = $state(false);
  result = $state<ResearchResult | null>(null);
  showDetails = $state(false);

  quickQuestion = $state("");
  quickLoading = $state(false);
  quickResult = $state<QueryResult | null>(null);

  async runResearch(prefill?: string) {
    const q = (prefill ?? this.query).trim();
    if (!q) return;
    this.query = q;
    this.loading = true;
    this.result = null;
    tabs.openResearchTab();
    try {
      this.result = await api.research(q);
      await connection.refreshStatus();
    } catch (e) {
      connection.connectionError = e instanceof Error ? e.message : "Research failed";
    } finally {
      this.loading = false;
    }
  }

  async runQuickQuery(question?: string) {
    const q = (question ?? this.quickQuestion).trim();
    if (!q) return;
    this.quickQuestion = q;
    this.quickLoading = true;
    this.quickResult = null;
    tabs.openQueryTab();
    try {
      this.quickResult = await api.query(q);
    } catch (e) {
      this.quickResult = {
        question: q,
        answer: e instanceof Error ? e.message : "Query failed",
        sources: [],
      };
    } finally {
      this.quickLoading = false;
    }
  }
}

export const research = new ResearchStore();