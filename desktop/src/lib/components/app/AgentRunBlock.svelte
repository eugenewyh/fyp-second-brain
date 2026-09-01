<script lang="ts">
  import type { AssistantTurn } from "$lib/stores/assistant.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import AgentWorkPanel from "./AgentWorkPanel.svelte";
  import ResearchReport from "$lib/components/research/ResearchReport.svelte";
  import FailRetry from "./FailRetry.svelte";
  import { extractOpenQuestions, questionFromGap } from "$lib/research/gaps";
  import { readNote } from "$lib/vault/load";

  type ResearchTurn = Extract<AssistantTurn, { kind: "research" }>;

  interface Props {
    turn: ResearchTurn;
    detailsOpen?: boolean;
    onToggleDetails?: () => void;
    onOpenPath?: (path: string) => void;
    onCancel?: () => void;
  }

  let {
    turn,
    detailsOpen = false,
    onToggleDetails,
    onOpenPath,
    onCancel,
  }: Props = $props();

  const live = $derived(turn.status === "running" || turn.status === "awaiting_plan");
  const done = $derived(turn.status === "done" && !!turn.result);
  const failed = $derived(turn.status === "error");

  const showActions = $derived(
    (!!turn.savedPath && !!onOpenPath) ||
      ((done || !!turn.livePlan || (turn.liveQueries?.length ?? 0) > 0) &&
        !!onToggleDetails &&
        !failed),
  );

  const claimCount = $derived(turn.claimCount ?? turn.result?.claim_count ?? 0);
  const remembered = $derived(
    done && (!!turn.indexed || claimCount > 0 || !!turn.memoryDetail),
  );
  const rememberedLabel = $derived(
    claimCount > 0
      ? `${claimCount} claim${claimCount === 1 ? "" : "s"} saved — View saved memory`
      : "Saved to memory — View saved memory",
  );
  const deepenGaps = $derived(
    done && turn.result?.report ? extractOpenQuestions(turn.result.report, 3) : [],
  );

  function fillDeepen(gap: string) {
    assistant.input = questionFromGap(gap);
    assistant.composerFocusNonce += 1;
  }

  let claimTitles = $state<string[]>([]);
  let claimPaths = $state<string[]>([]);
  let claimsLoaded = false;
  let claimsLoading = false;

  $effect(() => {
    if (claimsLoaded || claimsLoading || claimCount === 0) return;
    claimsLoading = true;
    void loadClaimTitles();
  });

  async function loadClaimTitles() {
    try {
      const slugs = turn.claimSlugs ?? turn.result?.claim_slugs ?? [];
      if (!slugs.length) {
        claimsLoaded = true;
        return;
      }
      // Resolve claim paths: same directory as the learning card when available.
      const learningPath = turn.learningPath || turn.result?.learning_path;
      const claimsDir = learningPath
        ? learningPath.replace(/\/memory\/.*$/, "") + "/memory/claims"
        : "";
      const titles: string[] = [];
      const paths: string[] = [];
      for (const slug of slugs.slice(0, 6)) {
        const path = claimsDir ? `${claimsDir}/${slug}.md` : "";
        if (path) {
          try {
            const md = await readNote(path);
            const m = md.match(/claim:\s*"(.*?)"/);
            const title = m?.[1] ?? slug.replace(/-/g, " ");
            titles.push(title);
            paths.push(path);
          } catch {
            titles.push(slug.replace(/-/g, " "));
            paths.push(path);
          }
        }
      }
      claimTitles = titles;
      claimPaths = paths;
      claimsLoaded = true;
    } finally {
      claimsLoading = false;
    }
  }

  /** Open the memory learning card in the standard reader (not the report). */
  async function openSavedMemory() {
    const direct = turn.learningPath || turn.result?.learning_path;
    if (direct) {
      onOpenPath?.(direct);
      return;
    }
    onToggleDetails?.();
  }

  function openClaim(index: number) {
    const path = claimPaths[index];
    if (path) onOpenPath?.(path);
  }
</script>

<article
  class="run"
  class:live
  class:done
  class:err={failed}
  data-testid="agent-run-block"
  data-turn-id={turn.id}
  data-status={turn.status}
>
  {#if live || done || failed}
    <AgentWorkPanel
      {turn}
      {detailsOpen}
      {onToggleDetails}
      {onCancel}
    />
  {/if}

  {#if failed}
    <FailRetry
      error={turn.error}
      disabled={assistant.sessionBusyForTurn(turn.id)}
      detailsOpen={detailsOpen}
      onRetry={() => void assistant.retryResearch(turn.id)}
      onDetails={onToggleDetails}
    />
  {:else if done && turn.result}
    <div class="report">
      <ResearchReport result={turn.result} variant="thread" />
    </div>
  {/if}

  {#if remembered}
    <button
      type="button"
      class="remembered"
      title="Open saved memory"
      onclick={() => void openSavedMemory()}
    >
      {rememberedLabel}
    </button>
    {#if claimTitles.length}
      <div class="claims-list">
        <p class="claims-label">Ideas saved</p>
        <ul class="claims-ul">
          {#each claimTitles as title, i}
            <li>
              <button
                type="button"
                class="claim-link"
                onclick={() => openClaim(i)}
                title={claimPaths[i]}
              >
                {title}
              </button>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  {/if}

  {#if showActions && !live}
    <div class="actions">
      {#if turn.savedPath && onOpenPath}
        <button
          type="button"
          class="link"
          data-testid="open-report"
          onclick={() => onOpenPath?.(turn.savedPath!)}
        >
          Open report
        </button>
      {/if}
      {#if (done || turn.livePlan || (turn.liveQueries?.length ?? 0) > 0) && onToggleDetails}
        <button type="button" class="link" onclick={onToggleDetails}>
          {detailsOpen ? "Hide details" : "Details"}
        </button>
      {/if}
    </div>
  {/if}

  {#if deepenGaps.length}
    <div class="deepen" role="group" aria-label="Deepen">
      {#each deepenGaps as gap}
        <button type="button" class="chip" onclick={() => fillDeepen(gap)}>
          {gap}
        </button>
      {/each}
    </div>
  {/if}
</article>

<style>
  .run {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    width: 100%;
  }

  .report {
    min-width: 0;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 0.85rem;
    align-items: center;
  }

  .link {
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 0;
  }

  .link:hover {
    color: var(--text);
    text-decoration: underline;
  }

  .remembered {
    align-self: flex-start;
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-faint);
    cursor: pointer;
    border-radius: 0;
  }

  .remembered:hover {
    color: var(--text-muted);
    text-decoration: underline;
  }

  .claims-list {
    margin-top: 0.35rem;
    padding: 0.35rem 0.6rem;
    border-left: 1px solid var(--border-subtle);
  }

  .claims-label {
    margin: 0 0 0.25rem;
    font-size: var(--text-xs);
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .claims-ul {
    margin: 0;
    padding-left: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .claim-link {
    background: none;
    border: none;
    padding: 0;
    min-height: auto;
    font-size: var(--text-sm);
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 0;
    text-align: left;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .claim-link:hover {
    color: var(--text);
    text-decoration: underline;
  }

  .deepen {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .chip {
    max-width: 100%;
    text-align: left;
    font-size: var(--text-sm);
    color: var(--text-muted);
    background: var(--control-fill);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 0.38rem 0.75rem;
    line-height: 1.4;
    cursor: pointer;
    transition:
      background var(--dur-control, 0.1s) var(--ease-out, ease),
      color var(--dur-control, 0.1s) var(--ease-out, ease),
      border-color var(--dur-control, 0.1s) var(--ease-out, ease);
  }

  .chip:hover {
    color: var(--text);
    background: var(--surface-hover);
    border-color: var(--border-active);
  }
</style>
