<script lang="ts">
  import type { ResearchResult } from "$lib/api";

  interface Props {
    query: string;
    result?: ResearchResult;
    confidence?: number;
    goalStatus?: string;
    runMode?: "studio" | "goal";
    savedPath?: string;
    learningPath?: string;
    indexed?: boolean;
    onOpenPath?: (path: string) => void;
    onDeepen?: () => void;
    onRerun?: () => void;
  }

  let {
    query,
    result,
    confidence,
    goalStatus = "",
    runMode = "studio",
    savedPath,
    learningPath,
    indexed = false,
    onOpenPath,
    onDeepen,
    onRerun,
  }: Props = $props();

  const conf = $derived(confidence ?? result?.confidence ?? null);
  const stats = $derived(result?.retrieval_stats ?? {});
  const revisions = $derived(result?.revision_count ?? 0);
  const passes = $derived(result?.pass_count ?? result?.passes?.length ?? 1);
  const reasons = $derived(result?.confidence_reasons ?? []);
</script>

<section class="run-summary" data-testid="run-summary">
  <header>
    <h3>Run summary</h3>
    <span class="badge">{runMode === "goal" ? "Goal" : "Studio"}</span>
  </header>

  <p class="q" title={query}>{query}</p>

  <dl class="metrics">
    <div>
      <dt>Confidence</dt>
      <dd>
        {conf != null ? `${Math.round(Number(conf) * 100)}%` : "—"}
      </dd>
    </div>
    <div>
      <dt>Revisions</dt>
      <dd>{revisions}</dd>
    </div>
    <div>
      <dt>Passes</dt>
      <dd>{passes}</dd>
    </div>
    {#if goalStatus}
      <div>
        <dt>Goal</dt>
        <dd>{goalStatus}</dd>
      </div>
    {/if}
  </dl>

  {#if Object.keys(stats).length}
    <p class="sources">
      Sources:
      {#each Object.entries(stats) as [k, v]}
        <span class="tag">{k} {v}</span>
      {/each}
    </p>
  {/if}

  {#if reasons.length}
    <ul class="reasons">
      {#each reasons.slice(0, 4) as r}
        <li>{r}</li>
      {/each}
    </ul>
  {/if}

  <div class="paths">
    {#if savedPath}
      <button type="button" class="link" onclick={() => onOpenPath?.(savedPath!)}>
        Open report note
      </button>
    {/if}
    {#if learningPath}
      <button type="button" class="link" onclick={() => onOpenPath?.(learningPath!)}>
        Open learning card
      </button>
    {/if}
    {#if indexed}
      <span class="indexed">Indexed in memory</span>
    {/if}
  </div>

  <div class="actions">
    {#if onDeepen}
      <button type="button" class="btn" onclick={onDeepen}>Deepen goal</button>
    {/if}
    {#if onRerun}
      <button type="button" class="btn ghost" onclick={onRerun}>Re-run</button>
    {/if}
  </div>
</section>

<style>
  .run-summary {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: 0.65rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  h3 {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
  }
  .badge {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    color: var(--text-muted);
    border: 1px solid var(--border-subtle);
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-xs);
  }
  .q {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.4rem;
    margin: 0;
  }
  .metrics div {
    padding: 0.35rem 0.45rem;
    border-radius: var(--radius-feedback);
    background: var(--bg);
    border: 1px solid var(--border-subtle);
  }
  dt {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  dd {
    margin: 0.1rem 0 0;
    font-family: var(--font-mono);
    font-size: var(--text-sm);
  }
  .sources {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-items: center;
  }
  .tag {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--border-subtle);
  }
  .reasons {
    margin: 0;
    padding-left: 1.1rem;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }
  .paths,
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    align-items: center;
  }
  .link {
    background: none;
    border: none;
    padding: 0;
    color: var(--text);
    font-size: var(--text-xs);
    text-decoration: underline;
    cursor: pointer;
  }
  .indexed {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    font-family: var(--font-mono);
  }
  .btn {
    font-size: var(--text-xs);
    padding: 0.3rem 0.55rem;
    border-radius: var(--radius-feedback);
    border: 1px solid var(--border-subtle);
    background: var(--text);
    color: var(--bg);
    cursor: pointer;
  }
  .btn.ghost {
    background: transparent;
    color: var(--text-muted);
  }
</style>
