<script lang="ts">
  import { onMount } from "svelte";
  import { readNote } from "$lib/vault/load";
  import { workspace } from "$lib/stores/workspace.svelte";
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

<section class="panel" role="region" aria-label="Note preview" onmouseup={onSelect}>
  <h2>{path.split("/").pop()}</h2>
  <p class="hint path-hint">{path}</p>

  {#if loading}
    <div class="loading">Loading note…</div>
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <pre class="raw-content">{content.slice(0, 8000)}{content.length > 8000 ? "\n…" : ""}</pre>
  {/if}
</section>

<style>
  .panel h2 {
    font-size: 1.2rem;
    margin-bottom: 0.2rem;
  }

  .path-hint {
    font-size: 0.75rem;
    margin-bottom: 1rem;
    word-break: break-all;
  }

  .raw-content {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    font-size: 0.8rem;
    white-space: pre-wrap;
    max-height: 70vh;
    overflow-y: auto;
    color: var(--text-muted);
  }

  .loading {
    color: var(--warning);
    padding: 1rem;
    background: var(--surface);
    border-radius: var(--radius);
  }

  .error {
    color: var(--error);
  }
</style>