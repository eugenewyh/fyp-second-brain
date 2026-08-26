/** Fixed LangGraph topology for Mission dashboard (Studio-inspired). */

export type AgentNodeId =
  | "planner"
  | "retriever"
  | "analyst"
  | "verifier"
  | "synthesizer";

export type AgentNodeStatus =
  | "pending"
  | "running"
  | "done"
  | "iterating"
  | "error"
  | "waiting_review";

export interface AgentNodeDef {
  id: AgentNodeId;
  label: string;
  short: string;
  /** SVG layout in viewBox 0..100 x 0..60 */
  x: number;
  y: number;
}

export const AGENT_NODES: AgentNodeDef[] = [
  { id: "planner", label: "Planner", short: "Plan", x: 10, y: 30 },
  { id: "retriever", label: "Retriever", short: "Retrieve", x: 30, y: 30 },
  { id: "analyst", label: "Analyst", short: "Analyse", x: 50, y: 30 },
  { id: "verifier", label: "Verifier", short: "Verify", x: 70, y: 30 },
  { id: "synthesizer", label: "Synthesizer", short: "Synthesize", x: 90, y: 30 },
];

/** Forward edges (straight path). Loop edge handled separately. */
export const AGENT_EDGES: { from: AgentNodeId; to: AgentNodeId }[] = [
  { from: "planner", to: "retriever" },
  { from: "retriever", to: "analyst" },
  { from: "analyst", to: "verifier" },
  { from: "verifier", to: "synthesizer" },
];

export const STEP_TO_NODE: Record<string, AgentNodeId> = {
  planning: "planner",
  searching: "retriever",
  analyzing: "analyst",
  reviewing: "verifier",
  writing: "synthesizer",
};

export const NODE_TO_STEP: Record<AgentNodeId, string> = {
  planner: "planning",
  retriever: "searching",
  analyst: "analyzing",
  verifier: "reviewing",
  synthesizer: "writing",
};

export function emptyAgentStatuses(): Record<AgentNodeId, AgentNodeStatus> {
  return {
    planner: "pending",
    retriever: "pending",
    analyst: "pending",
    verifier: "pending",
    synthesizer: "pending",
  };
}

export function statusesFromCompletedSteps(
  completed: string[],
  activeStep?: string,
): Record<AgentNodeId, AgentNodeStatus> {
  const s = emptyAgentStatuses();
  const order: AgentNodeId[] = [
    "planner",
    "retriever",
    "analyst",
    "verifier",
    "synthesizer",
  ];
  for (const step of completed) {
    const node = STEP_TO_NODE[step];
    if (node) s[node] = "done";
  }
  if (activeStep) {
    const node = STEP_TO_NODE[activeStep];
    if (node) s[node] = "running";
  }
  // Mark predecessors of active as done if not set
  if (activeStep) {
    const activeNode = STEP_TO_NODE[activeStep];
    const idx = order.indexOf(activeNode);
    for (let i = 0; i < idx; i++) {
      if (s[order[i]] === "pending") s[order[i]] = "done";
    }
  }
  return s;
}

export type ActivityTone = "default" | "live" | "success" | "warning" | "error";

export interface ActivityLogEntry {
  id: string;
  time: string;
  agent: string;
  message: string;
  tone: ActivityTone;
}

export function formatLogTime(d = new Date()): string {
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
