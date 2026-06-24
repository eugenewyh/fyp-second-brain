<script lang="ts">
  import type { ResearchResult } from "$lib/api";

  interface Props {
    chatMessage?: string;
    chatResponse?: string;
    chatLoading?: boolean;
    onChatSend?: (message: string) => void;
    researchResult?: ResearchResult | null;
    researchLoading?: boolean;
    quickSources?: { index: number; source: string; page: number | null }[];
  }

  let {
    chatMessage = $bindable(""),
    chatResponse = "",
    chatLoading = false,
    onChatSend,
    researchResult = null,
    researchLoading = false,
    quickSources = [],
  }: Props = $props();

  function sendChat() {
    if (!chatMessage.trim() || !onChatSend) return;
    onChatSend(chatMessage.trim());
  }

  function handleChatKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  }
</script>

<aside class="inspector-panel" data-testid="inspector-panel">
  <section class="inspector-section" data-testid="contextual-chat">
    <h3 class="section-title">Contextual AI Chat</h3>
    <div class="chat-box">
      <textarea
        bind:value={chatMessage}
        placeholder="Ask about the current note or research…"
        rows="3"
        onkeydown={handleChatKeydown}
        data-testid="inspector-chat-input"
      ></textarea>
      <button
        class="btn-primary chat-send"
        onclick={sendChat}
        disabled={chatLoading || !chatMessage.trim()}
      >
        {chatLoading ? "Thinking…" : "Send"}
      </button>
      {#if chatResponse}
        <div class="chat-response">{chatResponse}</div>
      {/if}
    </div>
  </section>

  <section class="inspector-section" data-testid="backlinks-section">
    <h3 class="section-title">Backlinks / Related Notes</h3>
    <ul class="placeholder-list">
      <li class="placeholder-item">No backlinks yet</li>
      <li class="placeholder-item muted">Related: servlets, HTTP lifecycle</li>
    </ul>
  </section>

  <section class="inspector-section" data-testid="agent-process-log">
    <h3 class="section-title">Agent Process Log</h3>
    {#if researchLoading}
      <p class="log-status">Running multi-agent pipeline…</p>
    {:else if researchResult}
      <div class="log-content">
        {#if researchResult.plan}
          <details open>
            <summary>Plan</summary>
            <pre>{researchResult.plan}</pre>
          </details>
        {/if}
        {#if researchResult.retrieval_log.length}
          <details>
            <summary>Retrieval log</summary>
            <pre>{researchResult.retrieval_log.join("\n")}</pre>
          </details>
        {/if}
        {#if Object.keys(researchResult.retrieval_stats).length}
          <details>
            <summary>Retrieval stats</summary>
            <pre>{JSON.stringify(researchResult.retrieval_stats, null, 2)}</pre>
          </details>
        {/if}
        {#if researchResult.revision_count}
          <p class="log-meta">Revisions: {researchResult.revision_count}</p>
        {/if}
      </div>
    {:else}
      <p class="log-empty">Run research to see agent steps</p>
    {/if}
  </section>

  <section class="inspector-section" data-testid="sources-section">
    <h3 class="section-title">Sources</h3>
    {#if quickSources.length}
      <ul class="sources-list">
        {#each quickSources as src}
          <li>[{src.index}] {src.source}{src.page ? `, p.${src.page}` : ""}</li>
        {/each}
      </ul>
    {:else if researchResult?.report}
      <p class="sources-hint">Sources appear in the research report</p>
    {:else}
      <p class="log-empty">No sources loaded</p>
    {/if}
  </section>
</aside>

<style>
  .inspector-panel {
    height: 100%;
    overflow-y: auto;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }

  .section-title {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.45rem;
  }

  .chat-box {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .chat-box textarea {
    font-size: 0.8rem;
    min-height: 60px;
  }

  .chat-send {
    align-self: flex-end;
    font-size: 0.8rem;
    padding: 0.4rem 0.75rem;
  }

  .chat-response {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.6rem;
    font-size: 0.8rem;
    line-height: 1.45;
    max-height: 120px;
    overflow-y: auto;
  }

  .placeholder-list {
    list-style: none;
    font-size: 0.8rem;
  }

  .placeholder-item {
    padding: 0.3rem 0;
    color: var(--text);
  }

  .placeholder-item.muted {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  .log-status {
    color: var(--warning);
    font-size: 0.8rem;
  }

  .log-empty,
  .sources-hint {
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .log-content {
    font-size: 0.75rem;
  }

  .log-content details {
    margin-bottom: 0.4rem;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.35rem 0.5rem;
  }

  .log-content summary {
    cursor: pointer;
    color: var(--accent);
    font-weight: 500;
  }

  .log-content pre {
    white-space: pre-wrap;
    color: var(--text-muted);
    margin-top: 0.35rem;
    font-size: 0.7rem;
  }

  .log-meta {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .sources-list {
    list-style: none;
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .sources-list li {
    padding: 0.2rem 0;
  }
</style>