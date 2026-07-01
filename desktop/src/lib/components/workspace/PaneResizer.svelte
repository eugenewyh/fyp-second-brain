<script lang="ts">
  interface Props {
    onResize: (delta: number) => void;
    onResizeEnd?: () => void;
  }

  let { onResize, onResizeEnd }: Props = $props();
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
    width: 2px;
    cursor: col-resize;
    background: transparent;
    flex-shrink: 0;
    transition: background 0.15s;
  }

  .pane-resizer:hover,
  .pane-resizer.dragging {
    background: var(--resizer-hover, var(--accent));
  }
</style>