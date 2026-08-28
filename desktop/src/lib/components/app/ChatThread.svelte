<script lang="ts">
  import { tick } from "svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import SourceChips from "$lib/components/ui/SourceChips.svelte";
  import AgentRunBlock from "./AgentRunBlock.svelte";
  import { markdownBodyToHtml } from "$lib/vault/markdown";
  import { formatDigestSummary } from "$lib/assistant/transparency";
  import { shouldAutoResearch } from "$lib/assistant/intent";
  import FailRetry from "./FailRetry.svelte";

  interface Props {
    onOpenPath?: (path: string) => void;
    onCancel?: () => void;
    onLookup?: (query: string) => void;
    onRetryAsk?: (turnId: string) => void;
    onTeach?: () => void;
    onViewMemory?: () => void;
  }

  let {
    onOpenPath,
    onCancel,
    onLookup,
    onRetryAsk,
    onTeach,
    onViewMemory,
  }: Props = $props();

  const routeCopy = $derived(
    assistant.routeStatus === "teach"
      ? "Remembering…"
      : assistant.routeStatus === "explain"
        ? "Asking from memory…"
        : assistant.routeStatus === "lookup"
          ? "Researching…"
          : null,
  );

  let scroller: HTMLDivElement | undefined = $state();

  const thread = $derived(assistant.getActiveThread());
  const empty = $derived(thread.length === 0);
  const detailsTurn = $derived(assistant.getMissionTurn());

  function priorUserText(turnId: string): string {
    const idx = thread.findIndex((t) => t.id === turnId);
    for (let i = idx - 1; i >= 0; i -= 1) {
      const t = thread[i];
      if (t?.kind === "user") return t.content;
    }
    return "";
  }

  function openPath(path: string) {
    if (onOpenPath) {
      onOpenPath(path);
      return;
    }
    app.openDocument(path, { from: "agent" });
    workspace.setActiveNote(path);
  }

  function rememberedCount(turn: {
    claimsCreated?: number;
    claimsRevised?: number;
  }): number {
    return (turn.claimsCreated ?? 0) + (turn.claimsRevised ?? 0);
  }

  async function scrollToBottom() {
    await tick();
    if (scroller) scroller.scrollTop = scroller.scrollHeight;
  }

  $effect(() => {
    void thread.length;
    void assistant.researchLoading;
    void assistant.quickLoading;
    void assistant.digestLoading;
    void assistant.routeStatus;
    void scrollToBottom();
  });
</script>

<div class="thread-wrap" data-testid="chat-thread">
  <div class="thread ui-scroll" bind:this={scroller}>
    {#if !empty}
      <div class="messages">
        {#each thread as turn (turn.id)}
          {#if turn.kind === "user"}
            <div class="row user-row">
              <div class="bubble user" data-testid="user-bubble">
                <p>{turn.content}</p>
              </div>
            </div>
          {:else if turn.kind === "manager"}
            <div class="row manager-row">
              <div class="bubble manager" data-testid="manager-bubble">
                <p class="job-label">Manager</p>
                <p>{turn.content}</p>
              </div>
            </div>
          {:else if turn.kind === "quick"}
            <div class="row ask-row">
              {#if turn.error}
                <FailRetry
                  error={turn.error}
                  disabled={assistant.isLoading || !onRetryAsk}
                  onRetry={() => onRetryAsk?.(turn.id)}
                />
              {:else}
                <div class="ask-body" data-testid="ask-bubble">
                  <p class="job-label">
                    {turn.thinMemory ? "Needs memory" : "Ask"}
                  </p>
                  <div class="ask-prose">
                    {@html markdownBodyToHtml(turn.content)}
                  </div>
                  {#if turn.sources.length}
                    <div class="sources">
                      <SourceChips
                        sources={turn.sources.slice(0, 6).map((s) => ({
                          index: s.index,
                          source: s.source,
                          page: s.page,
                        }))}
                        onOpen={openPath}
                      />
                      {#if turn.sources.length > 6}
                        <p class="more-src">+{turn.sources.length - 6} more sources</p>
                      {/if}
                    </div>
                  {/if}
                  {#if turn.thinMemory}
                    <div class="next-actions" data-testid="thin-memory-actions">
                      {#if onTeach}
                        <button
                          type="button"
                          class="action-btn primary"
                          data-testid="teach-first"
                          disabled={assistant.isLoading}
                          onclick={() => onTeach()}
                        >
                          Teach notes
                        </button>
                      {/if}
                      {#if onLookup && priorUserText(turn.id) && !shouldAutoResearch(priorUserText(turn.id))}
                        <button
                          type="button"
                          class="action-btn"
                          data-testid="look-this-up"
                          disabled={assistant.isLoading}
                          onclick={() => onLookup(priorUserText(turn.id))}
                        >
                          Look this up
                        </button>
                      {/if}
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {:else if turn.kind === "digest"}
            <div class="row digest-row">
              {#if turn.status === "error"}
                <FailRetry
                  error={turn.error}
                  disabled={assistant.isLoading ||
                    (!(turn.retryText || "").trim() && !(turn.retryPaths?.length))}
                  onRetry={() => void assistant.retryDigest(turn.id)}
                />
              {:else}
              <div class="digest-card" data-testid="digest-card">
                {#if turn.status === "running"}
                  <p class="digest-kicker">Remembering…</p>
                  <p class="digest-summary">{turn.label}</p>
                {:else}
                  <p class="digest-kicker">
                    {turn.idempotent ? "Already in memory" : "Remembered"}
                  </p>
                  <p class="digest-summary">{turn.summary || turn.label}</p>
                  <ul class="digest-meta">
                    <li>
                      {formatDigestSummary({
                        created: turn.claimsCreated ?? 0,
                        revised: turn.claimsRevised ?? 0,
                        dropped: turn.claimsDropped ?? 0,
                        idempotent: turn.idempotent,
                      })}
                    </li>
                    {#if turn.savedPath}
                      <li>
                        <button
                          type="button"
                          class="digest-link"
                          onclick={() => openPath(turn.savedPath ?? "")}
                        >
                          {turn.savedPath.split(/[\\/]/).pop()}
                        </button>
                      </li>
                    {/if}
                  </ul>
                  {#if rememberedCount(turn) > 0 || turn.idempotent}
                    <div class="next-actions">
                      {#if onViewMemory}
                        <button
                          type="button"
                          class="action-btn primary"
                          data-testid="view-memory"
                          onclick={() => onViewMemory()}
                        >
                          View memory
                          {#if rememberedCount(turn) > 0}
                            · {rememberedCount(turn)}
                          {/if}
                        </button>
                      {/if}
                    </div>
                  {/if}
                {/if}
              </div>
              {/if}
            </div>
          {:else if turn.kind === "research"}
            <div class="row run-row">
              <AgentRunBlock
                {turn}
                detailsOpen={assistant.inspectorOpen && detailsTurn?.id === turn.id}
                onToggleDetails={() => {
                  if (detailsTurn?.id !== turn.id) assistant.focusTurn(turn.id);
                  assistant.toggleInspector();
                }}
                onOpenPath={openPath}
                onCancel={onCancel}
              />
            </div>
          {/if}
        {/each}
        {#if routeCopy}
          <div class="row">
            <p class="route-status" role="status">{routeCopy}</p>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .thread-wrap {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .thread {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    padding: 1.35rem var(--chat-gutter, 1.5rem) 0.85rem;
  }

  .messages {
    width: min(var(--chat-col, 45rem), 100%);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    padding-bottom: 0.85rem;
  }

  .row {
    display: flex;
    width: 100%;
    justify-content: flex-start;
  }

  .ask-row,
  .run-row,
  .digest-row {
    justify-content: stretch;
  }

  .job-label {
    margin: 0 0 0.35rem;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent-live);
  }

  .digest-card {
    width: 100%;
    padding: 0.85rem 1rem;
    border: 1px solid color-mix(in srgb, var(--warning) 28%, var(--border));
    border-radius: var(--radius-xl);
    background: color-mix(in srgb, var(--warning) 6%, var(--bg-elevated));
  }

  .digest-kicker {
    margin: 0 0 0.25rem;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    color: var(--warning);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .digest-summary {
    margin: 0;
    color: var(--text);
    line-height: 1.45;
  }

  .digest-meta {
    margin: 0.45rem 0 0;
    padding: 0;
    list-style: none;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .digest-link {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent-live);
    cursor: pointer;
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }

  .next-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.7rem;
  }

  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    background: var(--bg-elevated);
    color: var(--text);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .action-btn:hover:not(:disabled) {
    background: var(--chrome-action-hover);
    border-color: var(--border-active);
  }

  .action-btn.primary {
    background: var(--accent);
    border-color: transparent;
    color: var(--accent-contrast);
  }

  .action-btn.primary:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .action-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .bubble.user {
    width: 100%;
    max-width: 100%;
    padding: 0.75rem 0.9rem;
    border-radius: var(--radius-lg);
    background: var(--bubble-user);
    color: var(--text);
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .bubble.manager {
    max-width: 100%;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .bubble.manager p {
    margin: 0;
  }

  .ask-body {
    width: 100%;
  }

  .ask-prose {
    color: var(--text);
    line-height: 1.55;
  }

  .ask-prose :global(p) {
    margin: 0 0 0.65rem;
  }

  .ask-prose :global(p:last-child) {
    margin-bottom: 0;
  }

  .sources {
    margin-top: 0.65rem;
  }

  .more-src {
    margin: 0.35rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .route-status {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--accent-live);
    font-weight: var(--font-medium);
  }

  .user-row {
    justify-content: flex-end;
  }

  .user-row .bubble.user {
    width: auto;
    max-width: min(36rem, 92%);
  }
</style>
