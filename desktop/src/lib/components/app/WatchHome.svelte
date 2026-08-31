<script lang="ts">
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import type { WatchListItem, WatchStatus } from "$lib/api";
  import WatchList from "./WatchList.svelte";
  import WatchEditor from "./WatchEditor.svelte";
  import WatchCreateModal from "./WatchCreateModal.svelte";

  let selected = $state<{
    projectPath: string;
    watchId: string;
  } | null>(null);
  let createOpen = $state(false);

  const topics = $derived(workspace.projectFolders);
  const initialTopicPath = $derived(workspace.activeTopicPath ?? topics[0]?.path ?? null);

  let seenWatchListNonce = app.watchListNonce;
  $effect(() => {
    const n = app.watchListNonce;
    if (n === seenWatchListNonce) return;
    seenWatchListNonce = n;
    selected = null;
  });

  function openItem(item: WatchListItem) {
    selected = { projectPath: item.project_path, watchId: item.watch_id || "legacy" };
  }

  function onCreated(_w: WatchStatus) {
    createOpen = false;
    workspace.requestVaultRefresh();
  }
</script>

<div class="watch-home">
  {#if selected}
    <WatchEditor
      projectPath={selected.projectPath}
      watchId={selected.watchId}
      onBack={() => (selected = null)}
      onMoved={(w) => {
        selected = { projectPath: w.project_path, watchId: w.watch_id || "legacy" };
      }}
    />
  {:else}
    <WatchList onOpen={openItem} onNew={() => (createOpen = true)} />
  {/if}
</div>

<WatchCreateModal
  open={createOpen}
  {initialTopicPath}
  onClose={() => (createOpen = false)}
  {onCreated}
/>

<style>
  .watch-home {
    display: flex;
    height: 100%;
    min-height: 0;
  }
  .watch-home :global(.watch-list),
  .watch-home :global(.editor) {
    flex: 1;
    min-height: 0;
  }
</style>
