<script lang="ts">
  import { onMount } from "svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import AppShell from "$lib/components/app/AppShell.svelte";

  onMount(() => {
    connection.connect();
  });
</script>

<AppShell />
