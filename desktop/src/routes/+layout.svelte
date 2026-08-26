<script lang="ts">
  import { onMount } from "svelte";
  import "../app.css";
  import { initTheme } from "$lib/theme/init-theme";

  onMount(() => {
    initTheme();
  });
</script>

<slot />
