<script lang="ts">
  import { app } from "$lib/stores/app.svelte";
  import type { WatchListItem } from "$lib/api";
  import WatchList, { type WatchDraft } from "./WatchList.svelte";
  import WatchEditor from "./WatchEditor.svelte";

  let selected = $state<{
    projectPath: string;
    watchId: string;
    draft?: { name: string; focus: string; include: string };
  } | null>(null);

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

  function openDraft(projectPath: string, draft: WatchDraft) {
    selected = { projectPath, watchId: "draft", draft };
  }
</script>

<div class="watch-home">
  {#if selected}
    <WatchEditor
      projectPath={selected.projectPath}
      watchId={selected.watchId}
      draft={selected.draft}
      onBack={() => (selected = null)}
      onMoved={(w) => {
        selected = { projectPath: w.project_path, watchId: w.watch_id || "legacy" };
      }}
      onRelocate={(path) => {
        if (selected?.draft) selected = { ...selected, projectPath: path };
      }}
    />
  {:else}
    <WatchList onOpen={openItem} onDraft={openDraft} />
  {/if}
</div>

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
