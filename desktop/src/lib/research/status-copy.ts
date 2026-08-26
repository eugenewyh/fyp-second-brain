/**
 * Human-readable status lines for agent runs (chat transcript).
 * Prefer short sentences; never dump source lists or raw plan text.
 */

import type { ActivityLogEntry, AgentNodeId, AgentNodeStatus } from "./agent-graph";

const NODE_LABEL: Record<AgentNodeId, string> = {
  planner: "Planner",
  retriever: "Retriever",
  analyst: "Analyst",
  verifier: "Verifier",
  synthesizer: "Synthesizer",
};

const DONE_DEFAULT: Record<AgentNodeId, string> = {
  planner: "Planner finished — approach ready",
  retriever: "Retriever finished — sources gathered",
  analyst: "Analyst finished — draft insights ready",
  verifier: "Verifier approved the analysis",
  synthesizer: "Synthesizer finished — report ready",
};

const RUNNING_DEFAULT: Record<AgentNodeId, string> = {
  planner: "Planner is breaking down the goal…",
  retriever: "Retriever is searching your library and the web…",
  analyst: "Analyst is extracting insights…",
  verifier: "Verifier is checking the analysis…",
  synthesizer: "Synthesizer is writing the report…",
};

const MANAGER_RUNNING: Record<AgentNodeId, string> = {
  planner: "Figuring out the approach…",
  retriever: "Checking your notes, then searching…",
  analyst: "Pulling insights…",
  verifier: "Checking the analysis…",
  synthesizer: "Writing it up…",
};

const MANAGER_DONE: Record<AgentNodeId, string> = {
  planner: "Approach ready",
  retriever: "Sources in",
  analyst: "Insights ready",
  verifier: "Checked the analysis",
  synthesizer: "Report ready",
};

/** Transcript voice: Manager, not named specialists. Details still uses statusLineForAgent. */
export function managerStatusLineForAgent(
  node: AgentNodeId,
  status: AgentNodeStatus,
  detail?: string | null,
): string {
  const d = cleanStatusDetail(detail);
  if (status === "running" || status === "waiting_review") {
    return d || MANAGER_RUNNING[node];
  }
  if (status === "iterating") {
    return d || "Revising the analysis…";
  }
  if (status === "error") {
    return d ? `Hit a snag — ${d}` : "Hit a snag";
  }
  if (status === "done") {
    if (d && !/^done$/i.test(d) && !/^running/i.test(d)) {
      return d;
    }
    return MANAGER_DONE[node];
  }
  return d || MANAGER_RUNNING[node];
}

/** Normalize noisy stream details into one short sentence. */
export function cleanStatusDetail(raw: string | undefined | null): string {
  if (!raw) return "";
  // Avoid pasting multi-line plans — take first line first
  let s = raw.trim().split("\n")[0]!.trim();
  s = s.replace(/\s+/g, " ");
  // Drop URL/path dumps and long comma lists
  if (s.length > 140) s = s.slice(0, 137) + "…";
  return s;
}

export function statusLineForAgent(
  node: AgentNodeId,
  status: AgentNodeStatus,
  detail?: string | null,
): string {
  const d = cleanStatusDetail(detail);
  if (status === "running" || status === "waiting_review") {
    return d || RUNNING_DEFAULT[node];
  }
  if (status === "iterating") {
    return d || "Verifier requested a revision — refining analysis…";
  }
  if (status === "error") {
    return d ? `${NODE_LABEL[node]} failed — ${d}` : `${NODE_LABEL[node]} failed`;
  }
  if (status === "done") {
    if (d && !/^done$/i.test(d) && !/^running/i.test(d)) {
      // Prefer a composed sentence when detail is already human
      if (/finished|approved|saved|wrote|recalled|ready|gathered/i.test(d)) {
        return d.startsWith(NODE_LABEL[node]) ? d : `${NODE_LABEL[node]} — ${d}`;
      }
      return `${NODE_LABEL[node]} finished — ${d}`;
    }
    return DONE_DEFAULT[node];
  }
  return d || `${NODE_LABEL[node]} pending`;
}

/** Map retrieval artifact stats to a short line. */
export function retrievalStatsLine(stats: Record<string, number | string> | undefined): string {
  if (!stats || !Object.keys(stats).length) return "Retriever finished — sources gathered";
  const parts: string[] = [];
  const personal = Number(stats.personal ?? stats.local ?? 0);
  const web = Number(stats.web ?? 0);
  const arxiv = Number(stats.arxiv ?? 0);
  if (personal > 0) parts.push(`${personal} from library`);
  if (web > 0) parts.push(`${web} web`);
  if (arxiv > 0) parts.push(`${arxiv} arXiv`);
  if (!parts.length) {
    const total = Object.values(stats).reduce<number>((a, v) => a + Number(v || 0), 0);
    if (total > 0) return `Retriever finished — ${total} sources`;
    return "Retriever finished — sources gathered";
  }
  return `Retriever finished — ${parts.join(", ")}`;
}

export type ReadableStatusLine = {
  id: string;
  text: string;
  tone: ActivityLogEntry["tone"];
  time?: string;
};

/**
 * Convert activity log into deduped, readable transcript lines.
 * Keeps order; collapses near-duplicate consecutive messages.
 */
export function readableStatusLines(log: ActivityLogEntry[] | undefined): ReadableStatusLine[] {
  if (!log?.length) return [];
  const out: ReadableStatusLine[] = [];
  let lastNorm = "";

  for (const entry of log) {
    const agent = (entry.agent || "").trim();
    const raw = cleanStatusDetail(entry.message);
    if (!raw) continue;

    let text = raw;
    const lowerAgent = agent.toLowerCase();
    const node = (["planner", "retriever", "analyst", "verifier", "synthesizer"] as AgentNodeId[]).find(
      (n) => n === lowerAgent || NODE_LABEL[n].toLowerCase() === lowerAgent,
    );

    // Rewrite crude "Done" / step ids
    if (node) {
      if (/^(done|running…|running\.\.\.)$/i.test(raw)) {
        text =
          entry.tone === "live" || entry.tone === "default"
            ? managerStatusLineForAgent(node, entry.tone === "live" ? "running" : "done")
            : managerStatusLineForAgent(node, entry.tone === "success" ? "done" : "running");
      } else if (/^(planning|searching|analyzing|reviewing|writing)$/i.test(raw)) {
        text = managerStatusLineForAgent(node, "running");
      } else if (!raw.toLowerCase().includes(NODE_LABEL[node].toLowerCase()) && entry.tone === "success") {
        text = managerStatusLineForAgent(node, "done", raw);
      } else if (entry.tone === "live" && !/…$|\.\.\.$|ing\b/i.test(raw)) {
        text = managerStatusLineForAgent(node, "running", raw);
      }
    } else if (lowerAgent === "memory") {
      if (/recalled/i.test(raw)) text = raw;
      else if (/wrote|saved|learning/i.test(raw)) text = raw.includes("memory") ? raw : `Memory — ${raw}`;
      else text = `Memory — ${raw}`;
    } else if (lowerAgent === "goal") {
      text = raw.startsWith("Pass") || raw.startsWith("Goal") ? raw : `Goal — ${raw}`;
    }

    // Soften artifact dumps like "personal:3 web:2"
    if (/^\w+:\d+(\s+\w+:\d+)*$/.test(raw)) {
      const stats: Record<string, number> = {};
      for (const part of raw.split(/\s+/)) {
        const [k, v] = part.split(":");
        if (k && v) stats[k] = Number(v);
      }
      text = retrievalStatsLine(stats);
    }

    const norm = text.toLowerCase().replace(/[.…]+$/g, "");
    if (norm === lastNorm) continue;
    // Also skip if previous line already said the same finished node
    if (out.length && out[out.length - 1]!.text.toLowerCase().startsWith(norm.slice(0, 24))) {
      const prev = out[out.length - 1]!;
      if (prev.tone !== "live" && entry.tone === "success") {
        out[out.length - 1] = { ...prev, text, tone: entry.tone, time: entry.time };
        lastNorm = norm;
        continue;
      }
    }
    lastNorm = norm;
    out.push({
      id: entry.id,
      text,
      tone: entry.tone,
      time: entry.time,
    });
  }

  return out.slice(-24);
}

export function outcomeLine(opts: {
  status: string;
  confidence?: number | null;
  goalStatus?: string;
  savedPath?: string;
  memoryDetail?: string;
  error?: string;
}): string {
  if (opts.status === "error") {
    return opts.error ? `Run failed — ${cleanStatusDetail(opts.error)}` : "Run failed";
  }
  if (opts.status === "awaiting_plan") return "Waiting for plan approval…";
  if (opts.status === "running") return "Working…";
  const conf =
    opts.confidence != null && !Number.isNaN(opts.confidence)
      ? ` · confidence ${Math.round(opts.confidence * 100)}%`
      : "";
  const goal = opts.goalStatus ? ` · ${opts.goalStatus}` : "";
  if (opts.memoryDetail && /not filed/i.test(opts.memoryDetail)) {
    return `${cleanStatusDetail(opts.memoryDetail)}${conf}${goal}`;
  }
  if (opts.savedPath) return `Report saved${conf}${goal}`;
  if (opts.memoryDetail) return `${cleanStatusDetail(opts.memoryDetail)}${conf}${goal}`;
  return `Mission complete${conf}${goal}`;
}

/** Calm title + hint for a failed run. Keep the raw error out of the primary line. */
export function failureCopy(error: string | undefined | null): { title: string; hint: string } {
  const raw = (error || "").trim();
  const lower = raw.toLowerCase();
  if (!raw) {
    return { title: "This run didn't finish", hint: "Retry the same question." };
  }
  if (
    /could not reach|connection error|failed to fetch|load failed|network request failed|networkerror|econnrefused|sidecar/i.test(
      lower,
    )
  ) {
    return {
      title: "Couldn't reach the AI service",
      hint: "Check you're online and the backend is running, then retry this run.",
    };
  }
  if (/rate limit|tokens per minute|\b429\b/.test(lower)) {
    return {
      title: "Rate limit reached",
      hint: "Wait a minute, then retry. Or switch provider in Settings.",
    };
  }
  if (/api key|not set|invalid key|byok/.test(lower)) {
    return {
      title: "API key needed",
      hint: "Open Settings → Providers, add a key, then retry.",
    };
  }
  if (/cancelled/.test(lower)) {
    return { title: "Cancelled", hint: "Retry if you still want this looked up." };
  }
  if (/timed out|timeout/.test(lower)) {
    return {
      title: "This run timed out",
      hint: "Retry, or ask a narrower question.",
    };
  }
  const title = raw.length > 140 ? `${raw.slice(0, 137)}…` : raw;
  return { title, hint: "Retry this run." };
}
