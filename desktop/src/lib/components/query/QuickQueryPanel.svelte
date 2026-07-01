<script lang="ts">
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";
  import Panel from "$lib/ui/Panel.svelte";
  import Button from "$lib/ui/Button.svelte";
</script>

<Panel title="Quick query" description="Fast RAG lookup against your vault">
  <input bind:value={research.quickQuestion} placeholder="Ask a question…" />
  <div class="actions">
    <Button
      variant="primary"
      onclick={() => research.runQuickQuery()}
      disabled={research.quickLoading || !connection.connected}
    >
      {research.quickLoading ? "Searching…" : "Ask"}
    </Button>
  </div>

  {#if research.quickResult}
    <div class="answer-box">
      <p class="answer">{research.quickResult.answer}</p>
      {#if research.quickResult.sources.length}
        <ul class="sources">
          {#each research.quickResult.sources as src}
            <li>
              <span class="idx">[{src.index}]</span>
              {src.source}{src.page ? ` · p.${src.page}` : ""}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</Panel>

<style>
  .actions {
    margin-top: 0.65rem;
    margin-bottom: 0.5rem;
  }

  .answer-box {
    margin-top: 1rem;
    padding: 0.85rem;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
  }

  .answer {
    font-size: 0.8125rem;
    color: var(--text-muted);
    line-height: 1.55;
  }

  .sources {
    margin-top: 0.65rem;
    list-style: none;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-faint);
  }

  .sources li {
    margin-bottom: 0.25rem;
  }

  .idx {
    color: var(--text-muted);
  }
</style>