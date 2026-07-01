<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { GraphData } from "$lib/vault/graph-data";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";

  interface Props {
    data: GraphData;
  }

  let { data }: Props = $props();
  let containerEl: HTMLDivElement | undefined = $state();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let graph: any = null;

  function openNode(id: string) {
    tabs.openNoteTab(id);
    workspace.setActiveNote(id);
  }

  onMount(async () => {
    if (!containerEl) return;
    const { default: ForceGraph } = await import("force-graph");
    const init = ForceGraph as unknown as () => (el: HTMLElement) => typeof graph;
    graph = init()(containerEl)
      .width(containerEl.clientWidth)
      .height(180)
      .nodeLabel((n: { label: string }) => n.label)
      .nodeColor((n: { isActive?: boolean }) => (n.isActive ? "#6b8cff" : "#5c5c66"))
      .linkColor(() => "#2a2a2f")
      .onNodeClick((n: { id: string }) => openNode(n.id))
      .graphData({ nodes: [], links: [] });
  });

  $effect(() => {
    graph?.graphData({
      nodes: data.nodes.map((n) => ({ ...n })),
      links: data.links.map((l) => ({ ...l })),
    });
    graph?.d3Force("charge")?.strength(-120);
  });

  onDestroy(() => {
    graph = null;
  });
</script>

<div class="knowledge-graph" bind:this={containerEl} role="img" aria-label="Knowledge graph"></div>

<style>
  .knowledge-graph {
    width: 100%;
    height: 180px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    overflow: hidden;
  }
</style>