<script lang="ts">
  import { onMount } from "svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import WorkspaceShell from "$lib/components/workspace/WorkspaceShell.svelte";

  onMount(() => {
    connection.connect();
  });
</script>

<WorkspaceShell />