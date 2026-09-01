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

  const routeStatus = $derived(assistant.routeStatus);
  const routeCopy = $derived(
    routeStatus === "teach"
      ? "Remembering"
      : routeStatus === "explain"
        ? "Asking from memory"
        : routeStatus === "lookup"
          ? "Researching"
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

  async function scrollToBottom(force = false) {
    await tick();
    if (!scroller) return;
    const distance = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    // Don't yank the viewport while the user is reading earlier turns
    if (!force && distance > 120) return;
    scroller.scrollTo({ top: scroller.scrollHeight, behavior: "smooth" });
  }

  /**
   * Cursor-style sticky stack: every user prompt that has scrolled past
   * stays pinned full-size; newer ones dock just under older ones.
   */
  function stickyUser(node: HTMLElement) {
    const root = node.closest(".thread");
    if (!(root instanceof HTMLElement)) return;

    const STICK_PAD = 8;
    const STACK_GAP = 8;

    const yInScroller = (el: HTMLElement) => {
      const er = el.getBoundingClientRect();
      const rr = root.getBoundingClientRect();
      return er.top - rr.top + root.scrollTop;
    };

    const syncAll = () => {
      const rows = [...root.querySelectorAll<HTMLElement>("[data-sticky-user]")];
      if (!rows.length) return;

      // Record natural Y while unpinned — stuck getBoundingClientRect is wrong for this
      for (const row of rows) {
        if (!row.classList.contains("is-stuck")) {
          row.dataset.stackY = String(yInScroller(row));
        }
      }

      const pinLine = root.scrollTop + STICK_PAD;
      const pinned = rows.map((row) => Number(row.dataset.stackY ?? 0) <= pinLine);

      let offset = STICK_PAD;
      for (let i = 0; i < rows.length; i += 1) {
        const row = rows[i];
        if (!pinned[i]) {
          row.classList.remove("is-stuck");
          row.style.top = "";
          row.style.zIndex = "";
          // Refresh natural Y now that it's flowing again
          row.dataset.stackY = String(yInScroller(row));
          continue;
        }

        row.classList.add("is-stuck");
        row.style.top = `${offset}px`;
        row.style.zIndex = String(30 + i);
        offset += row.getBoundingClientRect().height + STACK_GAP;
      }
    };

    const sync = () => {
      syncAll();
      requestAnimationFrame(syncAll);
    };

    root.addEventListener("scroll", sync, { passive: true });
    const ro = new ResizeObserver(sync);
    ro.observe(root);
    ro.observe(node);
    requestAnimationFrame(sync);

    return {
      destroy() {
        root.removeEventListener("scroll", sync);
        ro.disconnect();
        node.classList.remove("is-stuck");
        node.style.top = "";
        node.style.zIndex = "";
        delete node.dataset.stackY;
      },
    };
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
  <div class="thread-fade" aria-hidden="true"></div>
  <div class="thread ui-scroll" bind:this={scroller}>
    {#if !empty}
      <div class="messages">
        {#each thread as turn (turn.id)}
          {#if turn.kind === "user"}
            <div class="row user-row" data-sticky-user use:stickyUser>
              <div class="bubble user" data-testid="user-bubble">
                <p>{turn.content}</p>
              </div>
            </div>
          {:else if turn.kind === "manager"}
            <div class="row manager-row">
              <p class="status-line" data-testid="manager-bubble">{turn.content}</p>
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
                  {#if turn.thinMemory}
                    <div class="next-actions" data-testid="thin-memory-actions">
                      {#if onTeach}
                        <button
                          type="button"
                          class="action-btn"
                          data-testid="teach-first"
                          disabled={assistant.isLoading}
                          onclick={() => onTeach()}
                        >
                          Save notes
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
                          Research this
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
                {@const count = rememberedCount(turn)}
                {@const fileName = turn.savedPath
                  ? turn.savedPath.split(/[\\/]/).pop()
                  : null}
                {@const headline =
                  turn.status === "running"
                    ? turn.label || "Remembering…"
                    : turn.summary ||
                      turn.label ||
                      (turn.idempotent ? "Already in memory" : "Remembered")}
                {@const metaLine = formatDigestSummary({
                  created: turn.claimsCreated ?? 0,
                  revised: turn.claimsRevised ?? 0,
                  dropped: turn.claimsDropped ?? 0,
                  idempotent: false,
                })}
                <div
                  class="digest"
                  class:digest-live={turn.status === "running"}
                  data-testid="digest-card"
                >
                  <div class="digest-body">
                    <p
                      class="digest-headline"
                      class:status-shimmer={turn.status === "running"}
                    >
                      {headline}
                    </p>
                    {#if turn.status !== "running"}
                      <p class="digest-sub">
                        <span>
                          {turn.idempotent
                            ? "Already in memory"
                            : metaLine && metaLine !== "Remembered"
                              ? metaLine
                              : "Saved to memory"}
                        </span>
                        {#if fileName}
                          <span class="digest-dot" aria-hidden="true">·</span>
                          <button
                            type="button"
                            class="digest-file"
                            title={turn.savedPath}
                            onclick={() => openPath(turn.savedPath ?? "")}
                          >
                            {fileName}
                          </button>
                        {/if}
                      </p>
                    {/if}
                  </div>
                  {#if turn.status !== "running" && (count > 0 || turn.idempotent) && onViewMemory}
                    <button
                      type="button"
                      class="digest-cta"
                      data-testid="view-memory"
                      onclick={() => onViewMemory()}
                    >
                      View memory{#if count > 0}
                        <span class="digest-count">{count}</span>{/if}
                    </button>
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
          <div class="row route-row">
            <p class="route-status status-shimmer" role="status">{routeCopy}</p>
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
    position: relative;
  }

  /* Soft top edge so content doesn't guillotine under the header */
  .thread-fade {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1.25rem;
    z-index: 12;
    pointer-events: none;
    background: linear-gradient(
      to bottom,
      var(--bg) 0%,
      color-mix(in oklch, var(--bg) 70%, transparent) 45%,
      transparent 100%
    );
  }

  .thread {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    scroll-behavior: smooth;
    padding: 1.1rem var(--chat-gutter, 1.5rem) 0.85rem;
  }

  .messages {
    width: min(var(--chat-col, 45rem), 100%);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
    padding-bottom: 0.85rem;
  }

  .row {
    display: flex;
    width: 100%;
    justify-content: stretch;
  }

  .ask-row,
  .run-row,
  .digest-row,
  .user-row,
  .manager-row {
    justify-content: stretch;
  }

  /* Cursor-style: full prompts stick and pile under each other */
  .user-row {
    position: sticky;
    top: 0;
    z-index: 5;
    padding: 0;
    background: transparent;
  }

  .user-row.is-stuck {
    /* keep solid so scrolling content doesn't show through the stack */
    background: var(--bg);
    padding-bottom: 2px;
  }

  .user-row .bubble.user {
    transition: box-shadow 0.18s var(--ease-out, ease), border-color 0.18s var(--ease-out, ease);
  }

  .user-row.is-stuck .bubble.user {
    border-color: var(--border);
    box-shadow:
      0 1px 0 color-mix(in oklch, var(--border) 80%, transparent),
      0 8px 20px color-mix(in oklch, oklch(0 0 0) 22%, transparent);
  }

  /* Compact status banner — headline + meta + trailing action */
  .digest {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    width: 100%;
    max-width: 100%;
    padding: 0.7rem 0.85rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);
    box-shadow: var(--shadow-sm);
  }

  .digest-live {
    border-color: var(--border-active);
  }

  .digest-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .digest-headline {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    line-height: 1.4;
    color: var(--text);
  }

  .digest-sub {
    margin: 0.2rem 0 0;
    display: flex;
    align-items: center;
    gap: 0.35rem;
    min-width: 0;
    font-size: var(--text-sm);
    line-height: 1.4;
    color: var(--text-faint);
  }

  .digest-dot {
    color: var(--text-faint);
    flex-shrink: 0;
  }

  .digest-file {
    margin: 0;
    padding: 0;
    border: none;
    border-radius: 0;
    background: none;
    color: var(--text-muted);
    font: inherit;
    font-size: inherit;
    line-height: inherit;
    cursor: pointer;
    min-width: 0;
    min-height: auto;
    max-width: 16rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-decoration: none;
  }

  .digest-file:hover {
    color: var(--text);
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }

  .digest-cta {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    flex-shrink: 0;
    margin: 0;
    padding: 0.4rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    line-height: 1;
    cursor: pointer;
    min-height: auto;
    transition:
      background 0.12s ease,
      border-color 0.12s ease,
      color 0.12s ease;
  }

  .digest-cta:hover {
    background: var(--chrome-action-hover);
    border-color: var(--border-active);
    color: var(--text);
  }

  .digest-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.15rem;
    height: 1.15rem;
    padding: 0 0.3rem;
    border-radius: var(--radius-full);
    background: var(--control-fill);
    color: var(--text-faint);
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
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
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
    color: var(--text-muted);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .action-btn:hover:not(:disabled) {
    background: var(--chrome-action-hover);
    border-color: var(--border-active);
    color: var(--text);
  }

  .action-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .bubble.user {
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    padding: 0.85rem 1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    background: var(--bg-elevated);
    color: var(--text);
    line-height: 1.5;
    white-space: pre-wrap;
    box-shadow: var(--shadow-sm);
  }

  .bubble.user p {
    margin: 0;
  }

  /* Cursor-style system status — muted prose, no role chrome */
  .status-line {
    margin: 0;
    width: 100%;
    color: var(--text-muted);
    font-size: var(--text-base);
    line-height: 1.5;
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

  .ask-prose :global(ol),
  .ask-prose :global(ul) {
    margin: 0.35rem 0 0.65rem;
    padding-left: 1.4rem;
  }

  .ask-prose :global(ol) {
    list-style: decimal;
  }

  .ask-prose :global(ul) {
    list-style: disc;
  }

  .ask-prose :global(li) {
    margin: 0 0 0.4rem;
    padding-left: 0.15rem;
  }

  .ask-prose :global(li:last-child) {
    margin-bottom: 0;
  }

  .ask-prose :global(li > p) {
    margin: 0;
  }

  .sources {
    margin-top: 0.65rem;
  }

  .more-src {
    margin: 0.35rem 0 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .route-row {
    padding: 0.15rem 0;
  }

  .route-status {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-muted);
  }

  .status-shimmer {
    background: linear-gradient(
      90deg,
      var(--text-muted) 0%,
      var(--text) 45%,
      var(--text-muted) 90%
    );
    background-size: 200% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: status-shimmer 2.2s ease-in-out infinite;
  }

  @keyframes status-shimmer {
    0% {
      background-position: 100% center;
    }
    100% {
      background-position: -100% center;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .status-shimmer {
      animation: none;
      background: none;
      -webkit-background-clip: unset;
      background-clip: unset;
      color: var(--text-muted);
    }
  }
</style>
