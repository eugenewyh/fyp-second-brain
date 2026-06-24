<script lang="ts">
  import type { Snippet } from "svelte";
  import {
    applyResize,
    DEFAULT_LEFT_WIDTH,
    DEFAULT_RIGHT_WIDTH,
    MIN_PANE_WIDTH,
    MAX_PANE_WIDTH,
    SPLITTER_WIDTH,
    type ResizeSide,
  } from "$lib/workspace/resize";

  interface Props {
    left: Snippet;
    center: Snippet;
    right: Snippet;
    leftWidth?: number;
    rightWidth?: number;
  }

  let {
    left,
    center,
    right,
    leftWidth = $bindable(DEFAULT_LEFT_WIDTH),
    rightWidth = $bindable(DEFAULT_RIGHT_WIDTH),
  }: Props = $props();

  let dragging: ResizeSide | null = $state(null);
  let dragStartX = $state(0);
  let dragStartWidth = $state(0);

  function onSplitterPointerDown(side: ResizeSide, e: PointerEvent) {
    dragging = side;
    dragStartX = e.clientX;
    dragStartWidth = side === "left" ? leftWidth : rightWidth;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }

  function onSplitterPointerMove(e: PointerEvent) {
    if (!dragging) return;
    const delta = e.clientX - dragStartX;
    if (dragging === "left") {
      leftWidth = applyResize(dragStartWidth, delta, "left", MIN_PANE_WIDTH, MAX_PANE_WIDTH);
    } else {
      rightWidth = applyResize(dragStartWidth, delta, "right", MIN_PANE_WIDTH, MAX_PANE_WIDTH);
    }
  }

  function onSplitterPointerUp(e: PointerEvent) {
    if (!dragging) return;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    dragging = null;
  }
</script>

<div class="workspace-shell" data-testid="workspace-shell" class:dragging>
  <div
    class="pane pane-left"
    data-testid="pane-left"
    style:width="{leftWidth}px"
    style:min-width="{MIN_PANE_WIDTH}px"
    style:max-width="{MAX_PANE_WIDTH}px"
  >
    {@render left()}
  </div>

  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="splitter"
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize left panel"
    data-testid="splitter-left"
    style:width="{SPLITTER_WIDTH}px"
    onpointerdown={(e) => onSplitterPointerDown("left", e)}
    onpointermove={onSplitterPointerMove}
    onpointerup={onSplitterPointerUp}
    onpointercancel={onSplitterPointerUp}
  ></div>

  <div class="pane pane-center" data-testid="pane-center">
    {@render center()}
  </div>

  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="splitter"
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize right panel"
    data-testid="splitter-right"
    style:width="{SPLITTER_WIDTH}px"
    onpointerdown={(e) => onSplitterPointerDown("right", e)}
    onpointermove={onSplitterPointerMove}
    onpointerup={onSplitterPointerUp}
    onpointercancel={onSplitterPointerUp}
  ></div>

  <div
    class="pane pane-right"
    data-testid="pane-right"
    style:width="{rightWidth}px"
    style:min-width="{MIN_PANE_WIDTH}px"
    style:max-width="{MAX_PANE_WIDTH}px"
  >
    {@render right()}
  </div>
</div>

<style>
  .workspace-shell {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .workspace-shell.dragging {
    cursor: col-resize;
    user-select: none;
  }

  .pane {
    overflow: hidden;
    background: var(--surface);
    display: flex;
    flex-direction: column;
  }

  .pane-left {
    border-right: 1px solid var(--border);
    flex-shrink: 0;
  }

  .pane-center {
    flex: 1;
    min-width: 200px;
    background: var(--bg);
    overflow: hidden;
  }

  .pane-right {
    border-left: 1px solid var(--border);
    flex-shrink: 0;
  }

  .splitter {
    flex-shrink: 0;
    cursor: col-resize;
    background: transparent;
    position: relative;
    z-index: 2;
  }

  .splitter:hover,
  .workspace-shell.dragging .splitter {
    background: var(--accent);
    opacity: 0.35;
  }
</style>