<script lang="ts">
  interface Props {
    onResize: (delta: number) => void;
    onResizeEnd?: () => void;
    testId?: string;
  }

  let { onResize, onResizeEnd, testId = "splitter-left" }: Props = $props();
  let dragging = $state(false);

  function onPointerDown(e: PointerEvent) {
    dragging = true;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging) return;
    onResize(e.movementX);
  }

  function onPointerUp(e: PointerEvent) {
    if (!dragging) return;
    dragging = false;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    onResizeEnd?.();
  }
</script>

<div
  class="pane-resizer"
  data-testid={testId}
  class:dragging
  role="separator"
  aria-orientation="vertical"
  onpointerdown={onPointerDown}
  onpointermove={onPointerMove}
  onpointerup={onPointerUp}
  onpointercancel={onPointerUp}
></div>

<style>
  .pane-resizer {
    position: relative;
    width: 5px;
    margin: 0 -2px;
    cursor: col-resize;
    background: transparent;
    flex-shrink: 0;
    z-index: 6;
    touch-action: none;
  }

  .pane-resizer::after {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 1px;
    transform: translateX(-50%);
    background: transparent;
    transition: background 0.15s;
  }

  .pane-resizer:hover::after,
  .pane-resizer.dragging::after {
    background: var(--resizer-hover, var(--accent));
  }
</style>