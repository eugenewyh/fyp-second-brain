<script lang="ts">
  interface Props {
    online?: boolean;
  }

  let { online = false }: Props = $props();
</script>

<span class="status-dot" class:online aria-hidden="true"></span>

<style>
  .status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--error);
    flex-shrink: 0;
  }

  .status-dot.online {
    background: var(--success);
  }
</style>