<script lang="ts">
  import { onMount, type Snippet } from "svelte";
  import "../app.css";
  import { initTheme } from "$lib/theme/init-theme";

  let { children }: { children: Snippet } = $props();

  onMount(() => {
    initTheme();
  });
</script>

{@render children()}
