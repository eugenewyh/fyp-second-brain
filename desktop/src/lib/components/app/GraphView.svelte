<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { loadVaultTree, getVaultRoot, readNote } from "$lib/vault/load";
  import type { VaultNode } from "$lib/vault/types";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import { topicsFromTree } from "$lib/vault/topics";
  import {
    buildVaultGraph,
    selectBodiesToRead,
    vaultNodeTypeLabel,
    type VaultEdgeKind,
    type VaultGraphData,
    type VaultGraphNode,
  } from "$lib/vault/vault-graph";
  import {
    memory,
    GRAPH_TYPE_STYLE,
    GRAPH_TYPE_COLORS,
    GRAPH_TYPE_ORDER,
    type GraphTypeStyle,
  } from "$lib/stores/memory.svelte";
  import { THEME_CHANGE_EVENT } from "$lib/theme/apply-theme";
  import type { PeekNeighbor } from "$lib/vault/graph-peek";

  const TYPE_STYLE = GRAPH_TYPE_STYLE;
  const TYPE_COLORS = GRAPH_TYPE_COLORS;

  let tree = $state<VaultNode[]>([]);
  let bodies = $state<Record<string, string>>({});
  let loading = $state(true);
  let error = $state("");
  let containerEl = $state<HTMLDivElement | undefined>();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let graph = $state<any>(null);

  let hoveredId = $state<string | null>(null);
  let resizeHandler: (() => void) | null = null;
  let keyHandler: ((e: KeyboardEvent) => void) | null = null;
  /** Ignore background clicks that fire in the same gesture as a node click. */
  let ignoreBackgroundUntil = 0;
  let didFit = false;
  let textColor = "#252525";
  let textMuted = "#9d9d9d";
  let labelBg = "rgba(252, 252, 252, 0.82)";
  let accentLive = "#6f6f6f";
  let topicLinkStroke = "rgba(111, 111, 111, 0.55)";

  const topics = $derived(
    topicsFromTree(tree).filter((t) => !["research", "memory"].includes(t.name.toLowerCase())),
  );

  const data = $derived.by((): VaultGraphData => {
    return buildVaultGraph(tree, bodies, {
      types: memory.types,
      topicPath: memory.topicFilter,
    });
  });

  const searchNeedle = $derived(memory.search.trim().toLowerCase());
  const searchMatchIds = $derived.by(() => {
    if (!searchNeedle) return new Set<string>();
    const ids = new Set<string>();
    for (const n of data.nodes) {
      if (n.label.toLowerCase().includes(searchNeedle)) ids.add(n.id);
    }
    return ids;
  });

  function shortLabel(label: string, max = 18): string {
    const t = label.trim();
    if (t.length <= max) return t;
    return t.slice(0, max - 1) + "…";
  }

  function nodeId(n: { id?: string } | string | null | undefined): string {
    if (n == null) return "";
    if (typeof n === "string") return n;
    return n.id ?? "";
  }

  function neighborhood(id: string): Set<string> {
    const ids = new Set<string>([id]);
    for (const l of data.links) {
      if (l.source === id) ids.add(l.target);
      if (l.target === id) ids.add(l.source);
    }
    return ids;
  }

  function isSearching(): boolean {
    return searchNeedle.length > 0;
  }

  const neighborIds = $derived(
    memory.selected ? neighborhood(memory.selected.id) : new Set<string>(),
  );

  function isMatch(id: string): boolean {
    return searchMatchIds.has(id);
  }

  function isDimmed(id: string): boolean {
    if (isSearching()) return !searchMatchIds.has(id);
    if (!memory.selected) return false;
    if (hoveredId === id) return false;
    return !neighborIds.has(id);
  }

  function nodeRadius(n: VaultGraphNode): number {
    const base = n.type === "topic" ? 8 : 4.5;
    return base + Math.min(7, (n.degree ?? 0) * 0.75);
  }

  function hexToRgba(hex: string, alpha: number): string {
    const h = hex.replace("#", "");
    if (h.length !== 6) return `rgba(111, 111, 111, ${alpha})`;
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function readThemeColors() {
    if (typeof window === "undefined") return;
    const styles = getComputedStyle(document.documentElement);
    textColor = styles.getPropertyValue("--text").trim() || textColor;
    const faint = styles.getPropertyValue("--text-faint").trim();
    textMuted = faint || textMuted;
    labelBg = styles.getPropertyValue("--graph-label-bg").trim() || labelBg;
    accentLive = styles.getPropertyValue("--accent-live").trim() || accentLive;
    topicLinkStroke = hexToRgba(accentLive, 0.55);
    TYPE_STYLE.topic.fill = accentLive;
    TYPE_STYLE.topic.stroke = accentLive;
  }

  function onThemeChange() {
    readThemeColors();
    if (graph) graph.nodeRelSize(6);
  }

  function drawRoundedRect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    w: number,
    h: number,
    r: number,
  ) {
    const rr = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y, x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x, y + h, rr);
    ctx.arcTo(x, y + h, x, y, rr);
    ctx.arcTo(x, y, x + w, y, rr);
    ctx.closePath();
  }

  function paintNodeShape(
    ctx: CanvasRenderingContext2D,
    n: VaultGraphNode,
    x: number,
    y: number,
    r: number,
    style: GraphTypeStyle,
    dimmed: boolean,
    hovered: boolean,
    matched: boolean,
  ) {
    const alpha = dimmed ? 0.16 : 1;
    const isSelected = memory.selected?.id === n.id;
    ctx.save();
    ctx.globalAlpha = alpha;

    if (matched && !dimmed) {
      ctx.beginPath();
      ctx.arc(x, y, r + 7, 0, Math.PI * 2);
      ctx.fillStyle = hexToRgba(style.fill, 0.22);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, r + 4.5, 0, Math.PI * 2);
      ctx.strokeStyle = style.fill;
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.95;
      ctx.stroke();
      ctx.globalAlpha = alpha;
    }

    if (hovered || isSelected) {
      ctx.beginPath();
      ctx.arc(x, y, r + 3, 0, Math.PI * 2);
      ctx.strokeStyle = textColor;
      ctx.lineWidth = 1.2;
      ctx.globalAlpha = dimmed ? 0.3 : 0.72;
      ctx.stroke();
      ctx.globalAlpha = alpha;
    }

    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    if (n.type === "topic") {
      ctx.fillStyle = hexToRgba(style.stroke, 0.14);
      ctx.fill();
      ctx.strokeStyle = style.stroke;
      ctx.lineWidth = 1.4;
      ctx.stroke();
    } else {
      ctx.fillStyle = style.fill;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x - r * 0.22, y - r * 0.24, r * 0.38, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255, 255, 255, 0.22)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.strokeStyle = style.stroke;
      ctx.lineWidth = 0.9;
      ctx.stroke();
    }

    ctx.restore();
  }

  function paintNodeLabel(
    ctx: CanvasRenderingContext2D,
    n: VaultGraphNode,
    x: number,
    y: number,
    r: number,
    globalScale: number,
    dimmed: boolean,
    emphasized: boolean,
  ) {
    const fadeIn = 0.85;
    if (!emphasized && globalScale < fadeIn) return;
    const labelAlpha = emphasized ? 1 : Math.min(1, (globalScale - fadeIn) / 0.45);
    if (labelAlpha <= 0.05) return;

    const maxLen = globalScale < 1.15 && !emphasized ? 12 : 16;
    const label = shortLabel(n.label, maxLen);
    const fontSize = Math.max(10, 11 / Math.sqrt(Math.max(globalScale, 0.7)));
    ctx.save();
    ctx.font = `500 ${fontSize}px ${getComputedStyle(document.body).fontFamily || "system-ui, sans-serif"}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.globalAlpha = (dimmed ? 0.22 : 0.92) * labelAlpha;

    const metrics = ctx.measureText(label);
    const padX = 4;
    const padY = 2;
    const tw = metrics.width + padX * 2;
    const th = fontSize + padY * 2;
    const lx = x - tw / 2;
    const ly = y + r + 3;

    if (emphasized) {
      ctx.fillStyle = labelBg;
      drawRoundedRect(ctx, lx, ly, tw, th, 3);
      ctx.fill();
    }

    ctx.fillStyle = dimmed ? textMuted : textColor;
    ctx.fillText(label, x, ly + padY);
    ctx.restore();
  }

  function paintNode(
    n: VaultGraphNode & { x?: number; y?: number },
    ctx: CanvasRenderingContext2D,
    globalScale: number,
  ) {
    const x = n.x ?? 0;
    const y = n.y ?? 0;
    const r = nodeRadius(n);
    const style = TYPE_STYLE[n.type] ?? TYPE_STYLE.note;
    const dimmed = isDimmed(n.id);
    const hovered = hoveredId === n.id;
    const matched = isSearching() && isMatch(n.id);
    const emphasized = hovered || memory.selected?.id === n.id || matched;
    paintNodeShape(ctx, n, x, y, r, style, dimmed, hovered, matched);
    paintNodeLabel(ctx, n, x, y, r, globalScale, dimmed, emphasized);
  }

  function paintPointerArea(
    n: VaultGraphNode & { x?: number; y?: number },
    color: string,
    ctx: CanvasRenderingContext2D,
  ) {
    const x = n.x ?? 0;
    const y = n.y ?? 0;
    const r = nodeRadius(n) + 6;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function linkEndpoints(link: {
    source: unknown;
    target: unknown;
    kind?: VaultEdgeKind;
  }): { x1: number; y1: number; x2: number; y2: number; kind: VaultEdgeKind } | null {
    const s = link.source as { x?: number; y?: number; id?: string } | string;
    const t = link.target as { x?: number; y?: number; id?: string } | string;
    if (typeof s === "string" || typeof t === "string") return null;
    if (s?.x == null || s?.y == null || t?.x == null || t?.y == null) return null;
    return {
      x1: s.x,
      y1: s.y,
      x2: t.x,
      y2: t.y,
      kind: (link.kind ?? "wikilink") as VaultEdgeKind,
    };
  }

  function paintLink(
    link: { source: unknown; target: unknown; kind?: VaultEdgeKind },
    ctx: CanvasRenderingContext2D,
  ) {
    const ends = linkEndpoints(link);
    if (!ends) return;

    const sid = nodeId(link.source as { id?: string } | string);
    const tid = nodeId(link.target as { id?: string } | string);
    let dimmed = false;
    if (isSearching()) {
      dimmed = !(searchMatchIds.has(sid) && searchMatchIds.has(tid));
    } else if (memory.selected) {
      dimmed = !(neighborIds.has(sid) && neighborIds.has(tid));
    }

    ctx.save();
    ctx.globalAlpha = dimmed ? 0.1 : 0.72;
    ctx.beginPath();
    ctx.moveTo(ends.x1, ends.y1);
    ctx.lineTo(ends.x2, ends.y2);

    if (ends.kind === "topic") {
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = topicLinkStroke;
      ctx.lineWidth = 1.1;
    } else if (ends.kind === "provenance") {
      ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(181, 138, 79, 0.65)";
      ctx.lineWidth = 1.4;
    } else {
      ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(90, 100, 110, 0.55)";
      ctx.lineWidth = 1.7;
    }
    ctx.stroke();
    ctx.restore();
  }

  function syncGraphData() {
    if (!graph) return;
    graph.graphData({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.map((l) => ({ ...l })),
    });
    if (data.nodes.length > 0 && !didFit) {
      didFit = true;
      // Let the force settle briefly, then frame the cluster
      window.setTimeout(() => {
        try {
          graph?.zoomToFit?.(400, 72);
        } catch {
          /* ignore */
        }
      }, 350);
    }
  }

  function sizeGraph() {
    if (!graph || !containerEl) return;
    const w = containerEl.clientWidth;
    const h = containerEl.clientHeight;
    if (w > 0 && h > 0) {
      graph.width(w).height(h);
    }
  }

  function repaintGraph() {
    requestAnimationFrame(() => {
      sizeGraph();
      try {
        graph?.refresh?.();
      } catch {
        /* ignore */
      }
    });
  }

  function clearSelection() {
    memory.selected = null;
    hoveredId = null;
    repaintGraph();
  }

  async function refresh() {
    loading = true;
    error = "";
    didFit = false;
    try {
      const root = workspace.vaultRoot ?? (await getVaultRoot());
      workspace.vaultRoot = root;
      tree = await loadVaultTree(root);
      const files = selectBodiesToRead(flattenVaultFiles(tree));
      const next: Record<string, string> = {};
      await Promise.all(
        files.map(async (f) => {
          try {
            next[f.path] = await readNote(f.path);
          } catch {
            /* skip unreadable */
          }
        }),
      );
      bodies = next;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load vault";
    } finally {
      loading = false;
    }
  }

  function onNodeClick(node: VaultGraphNode, event?: MouseEvent) {
    event?.preventDefault?.();
    event?.stopPropagation?.();
    ignoreBackgroundUntil = performance.now() + 400;
    selectNode(node);
  }

  onMount(async () => {
    memory.selectNode = (n) => selectNode(n);
    memory.clearSelection = () => closePeek();
    memory.reload = () => void refresh();

    readThemeColors();
    await refresh();
    if (!containerEl) return;
    const { default: ForceGraph } = await import("force-graph");
    const init = ForceGraph as unknown as () => (el: HTMLElement) => unknown;
    const instance = init()(containerEl)
      .backgroundColor("rgba(0,0,0,0)")
      .nodeLabel(() => "")
      .autoPauseRedraw(false)
      .nodeRelSize(6)
      .nodeCanvasObject((n: VaultGraphNode & { x?: number; y?: number }, ctx, globalScale) => {
        paintNode(n, ctx, globalScale);
      })
      .nodePointerAreaPaint(
        (n: VaultGraphNode & { x?: number; y?: number }, color, ctx) => {
          paintPointerArea(n, color, ctx);
        },
      )
      .linkCanvasObject(
        (link: { source: unknown; target: unknown; kind?: VaultEdgeKind }, ctx) => {
          paintLink(link, ctx);
        },
      )
      .linkDirectionalParticles((l: { kind?: string }) => {
        if (l.kind === "provenance") return 3;
        if (l.kind === "wikilink") return 1;
        return 0;
      })
      .linkDirectionalParticleWidth((l: { kind?: string }) => (l.kind === "provenance" ? 2.2 : 1.4))
      .linkDirectionalParticleColor((l: { kind?: string }) =>
        l.kind === "provenance" ? "rgba(181, 138, 79, 0.9)" : "rgba(90, 100, 110, 0.55)",
      )
      .linkDirectionalParticleSpeed(0.004)
      .onNodeClick((n: VaultGraphNode, event: MouseEvent) => onNodeClick(n, event))
      .onNodeHover((n: VaultGraphNode | null) => {
        const id = n?.id ?? null;
        if (id === hoveredId) return;
        hoveredId = id;
      })
      .onBackgroundClick(() => {
        if (performance.now() < ignoreBackgroundUntil) return;
        closePeek();
      });
    instance.d3Force("charge")?.strength(-280);
    instance.d3Force("link")?.distance(90);
    graph = instance;
    sizeGraph();
    syncGraphData();

    const onResize = () => sizeGraph();
    window.addEventListener("resize", onResize);
    window.addEventListener(THEME_CHANGE_EVENT, onThemeChange);
    resizeHandler = onResize;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (!memory.selected && !app.documentPath) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      closePeek();
    };
    window.addEventListener("keydown", onKey, true);
    keyHandler = onKey;
    requestAnimationFrame(() => {
      sizeGraph();
      syncGraphData();
    });
  });

  onDestroy(() => {
    memory.reset();
    window.removeEventListener(THEME_CHANGE_EVENT, onThemeChange);
    if (resizeHandler) {
      window.removeEventListener("resize", resizeHandler);
      resizeHandler = null;
    }
    if (keyHandler) {
      window.removeEventListener("keydown", keyHandler, true);
      keyHandler = null;
    }
    if (graph) {
      try {
        graph.pauseAnimation?.();
        graph.graphData?.({ nodes: [], links: [] });
        if (typeof graph._destructor === "function") graph._destructor();
      } catch {
        /* ignore dispose errors */
      }
      graph = null;
    }
  });

  $effect(() => {
    void data.nodes;
    void data.links;
    void graph;
    syncGraphData();
  });

  $effect(() => {
    memory.counts = counts;
    memory.topics = topics;
    memory.totalFiles = data.totalFiles;
    memory.nodeCount = data.nodes.length;
    memory.truncated = data.truncated;
    memory.matchCount = searchNeedle ? searchMatchIds.size : 0;
  });

  $effect(() => {
    memory.neighbors = neighborRows;
    memory.selectedBody = memory.selected ? (bodies[memory.selected.id] ?? "") : "";
  });

  $effect(() => {
    const el = containerEl;
    if (!el) return;
    const ro = new ResizeObserver(() => repaintGraph());
    ro.observe(el);
    return () => ro.disconnect();
  });

  $effect(() => {
    const path = app.documentPath;
    if (!path && memory.selected && memory.selected.type !== "topic") {
      clearSelection();
    }
  });

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void refresh();
  });

  const counts = $derived.by(() => {
    const c: Record<string, number> = {};
    for (const n of data.nodes) c[n.type] = (c[n.type] ?? 0) + 1;
    return c;
  });

  const legendItems = GRAPH_TYPE_ORDER;

  const connected = $derived.by((): { incoming: PeekNeighbor[]; outgoing: PeekNeighbor[] } => {
    const sel = memory.selected;
    if (!sel) return { incoming: [], outgoing: [] };
    const byId = new Map(data.nodes.map((n) => [n.id, n]));
    const incoming: PeekNeighbor[] = [];
    const outgoing: PeekNeighbor[] = [];
    for (const l of data.links) {
      if (l.source === sel.id) {
        const node = byId.get(l.target);
        if (node) outgoing.push({ node, kind: l.kind });
      } else if (l.target === sel.id) {
        const node = byId.get(l.source);
        if (node) incoming.push({ node, kind: l.kind });
      }
    }
    return { incoming, outgoing };
  });

  const neighborRows = $derived.by((): PeekNeighbor[] => {
    return [...connected.outgoing, ...connected.incoming];
  });

  function closePeek() {
    clearSelection();
    if (app.documentPath) app.closeDocument();
  }

  function selectNode(node: VaultGraphNode) {
    const already = memory.selected?.id === node.id;
    memory.selected = node;
    if (node.type === "topic") {
      if (app.documentPath) app.closeDocument();
      return;
    }
    if (already && app.documentPath === node.id) return;
    app.openDocument(node.id, { label: node.label, from: "graph" });
    workspace.setActiveNote(node.id);
  }
</script>

<div class="graph-view">
  <div class="canvas-wrap">
    {#if loading && data.nodes.length === 0}
      <div class="state">
        <p class="state-title">Loading vault…</p>
      </div>
    {:else if error}
      <div class="state">
        <p class="state-title">Could not load graph</p>
        <p class="state-sub">{error}</p>
      </div>
    {:else if data.nodes.length === 0}
      <div class="state">
        <p class="state-title">Nothing to show yet</p>
        <p class="state-sub">Add notes, run research, or adjust the filters.</p>
      </div>
    {/if}

    <div
      class="canvas"
      bind:this={containerEl}
      role="img"
      aria-label="Knowledge graph"
    ></div>

    {#if data.nodes.length > 0}
      <div class="legend" aria-label="Graph legend">
        {#each legendItems as type (type)}
          <div class="legend-item">
            <span
              class="shape-swatch"
              class:topic={type === "topic"}
              style:--swatch={TYPE_COLORS[type]}
              style:--swatch-stroke={TYPE_STYLE[type].stroke}
            ></span>
            <span>{vaultNodeTypeLabel(type)}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .graph-view {
    display: flex;
    height: 100%;
    min-height: 0;
    background: var(--bg-elevated);
  }

  .shape-swatch {
    width: 10px;
    height: 10px;
    flex-shrink: 0;
    border-radius: 50%;
    background: var(--swatch);
    border: 1.5px solid var(--swatch-stroke, transparent);
    box-sizing: border-box;
  }

  .shape-swatch.topic {
    background: color-mix(in srgb, var(--swatch) 18%, transparent);
    border-width: 1.5px;
  }

  .canvas-wrap {
    position: relative;
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }

  .canvas {
    position: absolute;
    inset: 0;
    z-index: 1;
  }

  .legend {
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    z-index: 2;
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem 0.75rem;
    padding: 0.45rem 0.65rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);
    box-shadow: none;
    pointer-events: none;
  }

  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: var(--text-2xs);
    color: var(--text-muted);
    font-weight: var(--font-medium);
  }

  .state {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
    z-index: 3;
    pointer-events: none;
  }

  .state-title {
    margin: 0;
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
  }

  .state-sub {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }
</style>
