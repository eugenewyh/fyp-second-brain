<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
</script>

<div class="vault-status">
  <span class="status-dot" class:online={connection.connected}></span>
  {connection.connected
    ? `${connection.collectionCount} chunks indexed`
    : "Disconnected"}
  {#if connection.connectionError}
    <p class="error-text">{connection.connectionError}</p>
    <button class="btn-secondary retry-btn" onclick={() => connection.connect()}>Retry</button>
  {/if}
  <button class="btn-secondary ingest-btn" onclick={() => tabs.openIngestTab()}>
    Ingest folder
  </button>
</div>

<style>
  .vault-status {
    padding: 0.65rem;
    border-top: 1px solid var(--border);
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: auto;
  }

  .status-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--error);
    margin-right: 0.35rem;
  }

  .status-dot.online {
    background: var(--success);
  }

  .error-text {
    color: var(--error);
    margin-top: 0.35rem;
    font-size: 0.7rem;
  }

  .retry-btn,
  .ingest-btn {
    width: 100%;
    margin-top: 0.4rem;
    font-size: 0.75rem;
    padding: 0.35rem;
  }
</style>