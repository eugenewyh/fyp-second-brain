<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import StatusDot from "$lib/ui/StatusDot.svelte";
  import Button from "$lib/ui/Button.svelte";
</script>

<div class="vault-status">
  <div class="row">
    <StatusDot online={connection.connected} />
    <span class="label">
      {connection.connected ? `${connection.collectionCount} chunks` : "Offline"}
    </span>
  </div>
  {#if workspace.watcherStatus === "ingesting"}
    <p class="watcher">Ingesting…</p>
  {:else if workspace.watcherStatus !== "idle"}
    <p class="watcher err">{workspace.watcherStatus}</p>
  {/if}
  {#if connection.connectionError}
    <Button variant="ghost" onclick={() => connection.connect()}>Retry connection</Button>
  {/if}
  <Button variant="ghost" onclick={() => tabs.openIngestTab()}>Ingest folder</Button>
</div>

<style>
  .vault-status {
    padding: 0.5rem 0.65rem;
    border-top: 1px solid var(--border-subtle);
    font-size: 0.7rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 0.65rem;
  }

  .watcher {
    color: var(--accent);
    font-size: 0.65rem;
  }

  .watcher.err {
    color: var(--error);
  }
</style>