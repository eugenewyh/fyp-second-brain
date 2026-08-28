import type { ResearchResult } from "$lib/api";

export function formatRetrievalSummary(stats: Record<string, number>): string {
  const parts: string[] = [];
  const personal = stats.personal ?? stats.personal_docs ?? 0;
  const web = stats.web ?? 0;
  const arxiv = stats.arxiv ?? 0;

  if (personal > 0) {
    parts.push(`${personal} note${personal === 1 ? "" : "s"} from your library`);
  }
  if (web > 0) parts.push(`${web} web source${web === 1 ? "" : "s"}`);
  if (arxiv > 0) parts.push(`${arxiv} arXiv paper${arxiv === 1 ? "" : "s"}`);

  if (parts.length === 0) {
    const total = Object.values(stats).reduce((sum, n) => sum + n, 0);
    return total > 0
      ? `Based on ${total} source${total === 1 ? "" : "s"}`
      : "No sources from your notes or the web";
  }

  if (parts.length === 1) return `Based on ${parts[0]}`;
  if (parts.length === 2) return `Based on ${parts[0]} and ${parts[1]}`;
  return `Based on ${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

export function formatRevisionSummary(count: number): string {
  if (count <= 0) return "Verifier reviewed the analysis (no revision needed)";
  return `Verifier requested ${count} revision${count === 1 ? "" : "s"} (architectural self-critique)`;
}

export function formatDigestSummary(opts: {
  created?: number;
  revised?: number;
  dropped?: number;
  idempotent?: boolean;
}): string {
  const created = opts.created ?? 0;
  const revised = opts.revised ?? 0;
  const dropped = opts.dropped ?? 0;
  const parts: string[] = [];
  if (opts.idempotent) parts.push("Already in memory");
  if (created) parts.push(`${created} claim${created === 1 ? "" : "s"} remembered`);
  if (revised) parts.push(`${revised} updated`);
  if (dropped) parts.push(`${dropped} skipped`);
  return parts.join(" · ") || "Remembered";
}

export function retrievalOriginChips(stats: Record<string, number>): {
  key: string;
  label: string;
  count: number;
}[] {
  const personal = stats.personal ?? stats.personal_docs ?? 0;
  const web = stats.web ?? 0;
  const arxiv = stats.arxiv ?? 0;
  const chips: { key: string; label: string; count: number }[] = [];
  if (personal > 0) chips.push({ key: "personal", label: "Your library", count: personal });
  if (web > 0) chips.push({ key: "web", label: "Web", count: web });
  if (arxiv > 0) chips.push({ key: "arxiv", label: "arXiv", count: arxiv });
  return chips;
}

export function getLatestResearchResult(
  turns: { kind: string; result?: ResearchResult }[],
): ResearchResult | null {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    const turn = turns[i];
    if (turn.kind === "research" && turn.result) return turn.result;
  }
  return null;
}
