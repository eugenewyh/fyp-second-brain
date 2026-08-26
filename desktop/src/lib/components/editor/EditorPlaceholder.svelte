<script lang="ts">
  import { onMount } from "svelte";
  import { readNote } from "$lib/vault/load";
  import { workspace } from "$lib/stores/workspace.svelte";
  import Panel from "$lib/ui/Panel.svelte";
  import Button from "$lib/ui/Button.svelte";
  import { FileQuestion } from "@lucide/svelte";

  interface Props {
    path: string;
  }

  let { path }: Props = $props();
  let content = $state("");
  let loading = $state(true);
  let error = $state("");
  let showRaw = $state(false);

  const name = $derived(path.split("/").pop() ?? "File");
  const ext = $derived(name.includes(".") ? name.split(".").pop()?.toLowerCase() : "");

  onMount(async () => {
    loading = true;
    error = "";
    workspace.setActiveNote(path);
    try {
      content = await readNote(path);
    } catch (e) {
      error = e instanceof Error ? e.message : "Couldn't open this file";
    } finally {
      loading = false;
    }
  });

  function onSelect() {
    const sel = window.getSelection()?.toString() ?? "";
    if (sel) workspace.selectedText = sel;
  }
</script>

<Panel title={name} flush>
  {#if loading}
    <p class="ui-empty">Loading…</p>
  {:else if error}
    <div class="empty">
      <FileQuestion size={28} strokeWidth={1.5} />
      <p class="title">Couldn't open this file</p>
      <p class="desc">{error}</p>
      <Button variant="secondary" onclick={() => workspace.openUtilityPanel("ingest")}>
        Add documents
      </Button>
    </div>
  {:else}
    <div class="empty">
      <FileQuestion size={28} strokeWidth={1.5} />
      <p class="title">This file type can't be edited yet</p>
      <p class="desc">
        {#if ext}
          <code>.{ext}</code> files open as plain text for reference. Markdown notes and PDFs have full viewers.
        {:else}
          Open a markdown note or PDF for the best experience.
        {/if}
      </p>
      <Button variant="ghost" onclick={() => (showRaw = !showRaw)}>
        {showRaw ? "Hide content" : "Show text preview"}
      </Button>
    </div>
    {#if showRaw}
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <pre class="raw-content" onmouseup={onSelect}>{content.slice(0, 8000)}{content.length > 8000 ? "\n…" : ""}</pre>
    {/if}
  {/if}
</Panel>

<style>
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--space-2);
    padding: var(--space-6) var(--space-4);
    color: var(--text-faint);
  }

  .empty :global(svg) {
    margin-bottom: var(--space-1);
  }

  .title {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    color: var(--text);
  }

  .desc {
    font-size: var(--text-sm);
    max-width: 28rem;
    line-height: 1.5;
  }

  .desc code {
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .raw-content {
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius);
    padding: 1rem;
    font-size: var(--text-xs);
    font-family: var(--font-mono);
    white-space: pre-wrap;
    max-height: 50vh;
    overflow-y: auto;
    color: var(--text-muted);
    margin: 0 var(--space-4) var(--space-4);
  }
</style>
