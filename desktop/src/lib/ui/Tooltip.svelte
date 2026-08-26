<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    text: string;
    children: Snippet;
  }

  let { text, children }: Props = $props();
</script>

<span class="tooltip-wrap" title={text}>
  {@render children()}
</span>

<style>
  .tooltip-wrap {
    display: inline-flex;
    align-items: center;
  }
</style>
