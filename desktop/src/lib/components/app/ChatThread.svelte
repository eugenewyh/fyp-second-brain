<script lang="ts">
  import { tick } from "svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import SourceChips from "$lib/components/ui/SourceChips.svelte";
  import AgentRunBlock from "./AgentRunBlock.svelte";
  import { markdownBodyToHtml } from "$lib/vault/markdown";
  import { formatDigestSummary } from "$lib/assistant/transparency";
  import FailRetry from "./FailRetry.svelte";

  interface Props {
    onOpenPath?: (path: string) => void;
    onCancel?: () => void;
    onLookup?: (query: string) => void;
    onRetryAsk?: (turnId: string) => void;
  }

  let {
    onOpenPath,
    onCancel,
    onLookup,
    onRetryAsk,
  }: Props = $props();

  const routeCopy = $derived(
    assistant.routeStatus === "teach"
      ? "Filing into memory"
      : assistant.routeStatus === "explain"
        ? "Answering from memory"
        : assistant.routeStatus === "lookup"
          ? "Not in memory — looking up."
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
                  {#if turn.thinMemory && onLookup && priorUserText(turn.id)}
                    <button
                      type="button"
                      class="lookup-link"
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
                  <p class="digest-kicker">Filing into memory…</p>
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

  .digest-card {
    width: 100%;
    padding: 0.75rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    background: var(--control-fill);
  }

  .digest-kicker {
    margin: 0 0 0.25rem;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    letter-spacing: 0.02em;
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
    color: var(--accent, var(--text));
    cursor: pointer;
    text-decoration: underline;
  }

  .bubble.user {
    width: 100%;
    max-width: 100%;
    padding: 0.75rem 1rem;
    border-radius: var(--radius-xl);
    background: var(--bubble-user);
    color: var(--text);
    border: 1px solid var(--border);
    font-size: var(--type-body-md-size);
    font-weight: var(--type-body-md-weight);
    line-height: var(--type-body-md-leading);
  }

  .bubble.user p {
    margin: 0;
    white-space: pre-wrap;
  }

  .manager-row {
    justify-content: flex-start;
  }

  .bubble.manager {
    max-width: 28rem;
    padding: 0.55rem 0.85rem;
    border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-xs);
    background: var(--control-fill);
    color: var(--text);
    font-size: var(--type-body-sm-size);
    font-weight: var(--type-body-sm-weight);
    line-height: var(--type-body-sm-leading);
    border: 1px solid var(--border-subtle);
  }

  .bubble.manager p {
    margin: 0;
    white-space: pre-wrap;
  }

  .ask-body {
    width: 100%;
    color: var(--text);
  }

  .ask-body.err-bubble .err {
    margin: 0;
  }

  .ask-prose {
    font-size: var(--type-body-md-size);
    font-weight: var(--type-body-md-weight);
    line-height: 1.65;
    letter-spacing: var(--type-body-md-tracking);
    color: var(--text);
  }

  .ask-prose :global(> *:first-child) {
    margin-top: 0;
  }

  .ask-prose :global(> *:last-child) {
    margin-bottom: 0;
  }

  .ask-prose :global(p),
  .ask-prose :global(ul),
  .ask-prose :global(ol) {
    margin: 0 0 0.7rem;
  }

  .ask-prose :global(ul),
  .ask-prose :global(ol) {
    padding-left: 1.2rem;
  }

  .ask-prose :global(li) {
    margin-bottom: 0.5rem;
  }

  .ask-prose :global(h1),
  .ask-prose :global(h2),
  .ask-prose :global(h3) {
    margin: 1rem 0 0.45rem;
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
    line-height: 1.3;
    color: var(--text);
  }

  .ask-prose :global(h1) {
    font-size: var(--text-xl);
  }

  .ask-prose :global(h2),
  .ask-prose :global(h3) {
    font-size: var(--text-lg);
  }

  .ask-prose :global(strong) {
    font-weight: var(--font-semibold);
  }

  .ask-prose :global(code) {
    font-family: var(--font-mono);
    font-size: 0.88em;
    background: var(--control-fill);
    border-radius: var(--radius-sm);
    padding: 0.08em 0.32em;
  }

  .ask-prose :global(pre) {
    margin: 0 0 0.7rem;
    padding: 0.7rem 0.85rem;
    background: var(--control-fill);
    border-radius: var(--radius-md);
    overflow-x: auto;
  }

  .ask-prose :global(pre code) {
    background: none;
    padding: 0;
  }

  .route-status {
    margin: 0.15rem 0 0.35rem;
    color: var(--text-muted);
    font-size: var(--text-sm);
  }

  .sources {
    margin-top: 0.7rem;
  }

  .err {
    color: var(--error);
    font-size: var(--text-base);
    line-height: 1.5;
  }

  .more-src {
    margin: 0.35rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-muted);
  }

  .lookup-link {
    display: inline-block;
    margin-top: 0.7rem;
    background: none;
    border: none;
    padding: 0;
    color: var(--accent, var(--text));
    cursor: pointer;
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
  }

  .lookup-link:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
