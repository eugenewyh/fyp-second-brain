<script lang="ts">
  import type { CritiqueHistoryEntry, ResearchResult } from "$lib/api";
  import Badge from "$lib/ui/Badge.svelte";
  import SectionHeader from "$lib/ui/SectionHeader.svelte";

  interface Props {
    history?: CritiqueHistoryEntry[];
    result?: ResearchResult | null;
    class?: string;
  }

  let { history = [], result = null, class: className = "" }: Props = $props();

  const entries = $derived(
    history.length
      ? history
      : result?.critique_history?.length
        ? result.critique_history
        : [],
  );

  const forced = $derived(
    entries.some((e) => e.critique?.source === "forced_max_revisions") ||
      result?.critique_structured?.source === "forced_max_revisions",
  );
</script>

<section class="critique-panel {className}" data-testid="self-critique-panel">
  <SectionHeader
    title="Self-critique"
    subtitle={entries.length
      ? `${entries.length} verifier pass${entries.length === 1 ? "" : "es"}`
      : "No critique yet"}
    mono
  />

  {#if forced}
    <div class="forced">
      <Badge variant="warning">Forced max revisions</Badge>
      <span>Proceeded with best available analysis</span>
    </div>
  {/if}

  {#if entries.length === 0 && result?.critique}
    <div class="pass">
      <div class="pass-head">
        <Badge variant={result.critique_approved ? "success" : "warning"}>
          {result.critique_approved ? "approved" : "revise"}
        </Badge>
        <span class="src">latest</span>
      </div>
      <pre class="summary">{result.critique}</pre>
    </div>
  {:else if entries.length === 0}
    <p class="empty">Verifier output will appear here during research.</p>
  {:else}
    <ol class="timeline">
      {#each entries as entry, i (entry.ts ?? i)}
        {@const c = entry.critique}
        <li class="pass">
          <div class="pass-head">
            <span class="idx">#{entry.revision_index ?? i}</span>
            <Badge
              variant={c?.verdict === "approved"
                ? "success"
                : c?.source === "forced_max_revisions"
                  ? "warning"
                  : "warning"}
            >
              {c?.source === "forced_max_revisions"
                ? "forced"
                : c?.verdict ?? "—"}
            </Badge>
            <span class="src">{c?.source ?? ""}</span>
            {#if entry.ts}
              <span class="ts">{entry.ts.slice(11, 19)}</span>
            {/if}
          </div>
          {#if c?.summary}
            <pre class="summary">{c.summary}</pre>
          {/if}
          {#if c?.issues?.length}
            <ul class="issues">
              {#each c.issues as issue}
                <li>
                  <Badge
                    variant={issue.severity === "blocking"
                      ? "error"
                      : issue.severity === "major"
                        ? "warning"
                        : "default"}
                  >
                    {issue.code}
                  </Badge>
                  <span>{issue.message}</span>
                </li>
              {/each}
            </ul>
          {/if}
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  .critique-panel {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: var(--space-3);
    min-width: 0;
  }

  .forced {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.65rem;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .empty {
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .timeline {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .pass {
    border-left: 2px solid var(--border);
    padding-left: 0.65rem;
  }

  .pass-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
    margin-bottom: 0.35rem;
  }

  .idx {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .src {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    color: var(--text-faint);
    text-transform: uppercase;
  }

  .ts {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    color: var(--text-faint);
    margin-left: auto;
  }

  .summary {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-muted);
    white-space: pre-wrap;
    line-height: 1.45;
    margin: 0;
  }

  .issues {
    list-style: none;
    margin-top: 0.4rem;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .issues li {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-items: flex-start;
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.4;
  }
</style>
