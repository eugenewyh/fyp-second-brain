<script lang="ts">
  import type { Snippet } from "svelte";
  import {
    applyResize,
    constrainPaneWidths,
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

  let shellEl: HTMLDivElement | undefined = $state();
  let containerWidth = $state(1200);
  let dragging: ResizeSide | null = $state(null);
  let dragStartX = $state(0);
  let dragStartWidth = $state(0);

  function syncContainerWidth() {
    if (shellEl) {
      containerWidth = shellEl.clientWidth;
      const constrained = constrainPaneWidths(leftWidth, rightWidth, containerWidth);
      leftWidth = constrained.leftWidth;
      rightWidth = constrained.rightWidth;
    }
  }

  function applyDrag(deltaX: number) {
    if (!dragging) return;
    const next =
      dragging === "left"
        ? applyResize(dragStartWidth, deltaX, "left", MIN_PANE_WIDTH, MAX_PANE_WIDTH)
        : applyResize(dragStartWidth, deltaX, "right", MIN_PANE_WIDTH, MAX_PANE_WIDTH);

    const constrained = constrainPaneWidths(
      dragging === "left" ? next : leftWidth,
      dragging === "right" ? next : rightWidth,
      containerWidth,
    );
    leftWidth = constrained.leftWidth;
    rightWidth = constrained.rightWidth;
  }

  function onWindowPointerMove(e: PointerEvent) {
    applyDrag(e.clientX - dragStartX);
  }

  function endDrag() {
    dragging = null;
    window.removeEventListener("pointermove", onWindowPointerMove);
    window.removeEventListener("pointerup", endDrag);
    window.removeEventListener("pointercancel", endDrag);
  }

  function onSplitterPointerDown(side: ResizeSide, e: PointerEvent) {
    dragging = side;
    dragStartX = e.clientX;
    dragStartWidth = side === "left" ? leftWidth : rightWidth;
    syncContainerWidth();
    window.addEventListener("pointermove", onWindowPointerMove);
    window.addEventListener("pointerup", endDrag);
    window.addEventListener("pointercancel", endDrag);
    e.preventDefault();
  }

  $effect(() => {
    if (!shellEl) return;
    syncContainerWidth();
    const observer = new ResizeObserver(() => syncContainerWidth());
    observer.observe(shellEl);
    return () => observer.disconnect();
  });
</script>

<div bind:this={shellEl} class="workspace-shell" data-testid="workspace-shell" class:dragging>
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
    touch-action: none;
  }

  .splitter:hover,
  .workspace-shell.dragging .splitter {
    background: var(--accent);
    opacity: 0.35;
  }
</style>