import type { VaultGraphNode, VaultNodeType } from "$lib/vault/vault-graph";
import type { PeekNeighbor } from "$lib/vault/graph-peek";

export interface GraphTypeStyle {
  fill: string;
  stroke: string;
}

/** Quiet type tints; geometry is always a circle (Obsidian-like). */
export const GRAPH_TYPE_STYLE: Record<VaultNodeType, GraphTypeStyle> = {
  note: { fill: "#6d7a86", stroke: "#4a5560" },
  research: { fill: "#6b82c4", stroke: "#445a96" },
  learning: { fill: "#c49a4a", stroke: "#8f6d2e" },
  digest: { fill: "#8b72b0", stroke: "#5e4a7a" },
  topic: { fill: "#8a8a8a", stroke: "#6f6f6f" },
};

export const GRAPH_TYPE_COLORS: Record<VaultNodeType, string> = {
  note: GRAPH_TYPE_STYLE.note.fill,
  research: GRAPH_TYPE_STYLE.research.fill,
  learning: GRAPH_TYPE_STYLE.learning.fill,
  digest: GRAPH_TYPE_STYLE.digest.fill,
  topic: GRAPH_TYPE_STYLE.topic.stroke,
};

export const GRAPH_TYPE_ORDER: VaultNodeType[] = [
  "note",
  "research",
  "learning",
  "digest",
  "topic",
];

/**
 * Shared state for Memory mode: the sidebar owns controls (scope, search,
 * type filters, selection details) and GraphView owns the canvas + data.
 * GraphView publishes derived data here and registers node actions.
 */
class MemoryStore {
  // Controls (sidebar writes, graph reads)
  search = $state("");
  topicFilter = $state<string | null>(null);
  types = $state<Record<VaultNodeType, boolean>>({
    note: true,
    research: true,
    learning: true,
    digest: true,
    topic: true,
  });
  selected = $state<VaultGraphNode | null>(null);

  // Published by GraphView
  counts = $state<Record<string, number>>({});
  topics = $state<{ name: string; path: string }[]>([]);
  neighbors = $state<PeekNeighbor[]>([]);
  selectedBody = $state("");
  totalFiles = $state(0);
  nodeCount = $state(0);
  truncated = $state(false);
  matchCount = $state(0);

  // Actions registered by GraphView while mounted
  selectNode: (node: VaultGraphNode) => void = () => {};
  clearSelection: () => void = () => {};
  reload: () => void = () => {};

  toggleType(t: VaultNodeType) {
    this.types = { ...this.types, [t]: !this.types[t] };
  }

  /** Enter Memory mode scoped to a topic (null = all workspaces). */
  open(topicPath: string | null) {
    this.topicFilter = topicPath;
    this.search = "";
    this.selected = null;
    this.neighbors = [];
    this.selectedBody = "";
  }

  /** Leaving Memory mode — drop published data and callbacks. */
  reset() {
    this.search = "";
    this.topicFilter = null;
    this.types = { note: true, research: true, learning: true, digest: true, topic: true };
    this.selected = null;
    this.counts = {};
    this.topics = [];
    this.neighbors = [];
    this.selectedBody = "";
    this.totalFiles = 0;
    this.nodeCount = 0;
    this.truncated = false;
    this.matchCount = 0;
    this.selectNode = () => {};
    this.clearSelection = () => {};
    this.reload = () => {};
  }
}

export const memory = new MemoryStore();
