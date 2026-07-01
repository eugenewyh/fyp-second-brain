<script lang="ts">
  import { onMount } from "svelte";
  import { readNote } from "$lib/vault/load";
  import { workspace } from "$lib/stores/workspace.svelte";
  import Panel from "$lib/ui/Panel.svelte";

  interface Props {
    path: string;
  }

  let { path }: Props = $props();
  let content = $state("");
  let loading = $state(true);
  let error = $state("");

  onMount(async () => {
    loading = true;
    error = "";
    workspace.setActiveNote(path);
    try {
      content = await readNote(path);
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to read note";
    } finally {
      loading = false;
    }
  });

  function onSelect() {
    const sel = window.getSelection()?.toString() ?? "";
    if (sel) workspace.selectedText = sel;
  }
</script>

<Panel title={path.split("/").pop() ?? "File"} flush>
  {#if loading}
    <p class="ui-empty">Loading…</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <pre class="raw-content" onmouseup={onSelect}>{content.slice(0, 8000)}{content.length > 8000 ? "\n…" : ""}</pre>
  {/if}
</Panel>

<style>
  .raw-content {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    padding: 1rem;
    font-size: 0.75rem;
    font-family: var(--font-mono);
    white-space: pre-wrap;
    max-height: 70vh;
    overflow-y: auto;
    color: var(--text-muted);
  }

  .error {
    color: var(--error);
    font-size: 0.75rem;
  }
</style>