<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { chat } from "$lib/stores/chat.svelte";
  import { readNote } from "$lib/vault/load";
  import { splitFrontmatter } from "$lib/vault/markdown";
  import Button from "$lib/ui/Button.svelte";
  import { Send } from "@lucide/svelte";

  let message = $state("");
  let noteExcerpt = $state("");

  const thread = $derived(chat.getThread(workspace.activeNotePath));

  async function loadNoteExcerpt(path: string | null) {
    if (!path || !path.endsWith(".md")) {
      noteExcerpt = "";
      return;
    }
    try {
      const raw = await readNote(path);
      noteExcerpt = splitFrontmatter(raw).body.slice(0, 2000);
    } catch {
      noteExcerpt = "";
    }
  }

  $effect(() => {
    void loadNoteExcerpt(workspace.activeNotePath);
  });

  async function send() {
    if (!message.trim() || !connection.connected || chat.loading) return;
    const text = message;
    message = "";
    await chat.send(workspace.activeNotePath, text, {
      note_path: workspace.activeNotePath,
      selected_text: workspace.selectedText || null,
      note_excerpt: noteExcerpt || null,
    });
  }

  function viewSources() {
    workspace.inspectorTab = "sources";
  }

  function clearChat() {
    chat.clearThread(workspace.activeNotePath);
  }
</script>

<div class="chat-pane">
  <p class="context">
    {#if workspace.activeNotePath}
      <span class="note-name">{workspace.activeNotePath.split("/").pop()}</span>
      {#if workspace.selectedText}<span class="selection"> · selection</span>{/if}
    {:else}
      <span class="faint">No note open</span>
    {/if}
  </p>

  <div class="messages ui-scroll" aria-live="polite">
    {#if thread.length === 0}
      <p class="ui-empty">Ask about the open note or your vault</p>
    {:else}
      {#each thread as turn}
        <div class="bubble" class:user={turn.role === "user"} class:assistant={turn.role === "assistant"}>
          <p>{turn.content}</p>
          {#if turn.role === "assistant" && turn.sources?.length}
            <button class="link-btn" onclick={viewSources}>Sources ({turn.sources.length})</button>
          {/if}
        </div>
      {/each}
    {/if}
    {#if chat.loading}
      <p class="thinking">Thinking…</p>
    {/if}
    {#if chat.error}
      <p class="error">{chat.error}</p>
    {/if}
  </div>

  {#if thread.length}
    <div class="top-actions">
      <Button variant="ghost" onclick={clearChat} disabled={chat.loading}>Clear</Button>
    </div>
  {/if}

  <div class="input-row">
    <input
      bind:value={message}
      placeholder="Message…"
      onkeydown={(e) => e.key === "Enter" && !e.shiftKey && send()}
      disabled={!connection.connected || chat.loading}
    />
    <Button
      variant="primary"
      onclick={send}
      disabled={!connection.connected || chat.loading}
      title="Send"
    >
      <Send size={14} strokeWidth={1.75} />
    </Button>
  </div>
</div>

<style>
  .chat-pane {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 0.5rem 0.65rem 0.65rem;
    gap: 0.4rem;
  }

  .context {
    font-size: 0.65rem;
    color: var(--text-faint);
    font-family: var(--font-mono);
  }

  .note-name {
    color: var(--text-muted);
  }

  .selection {
    color: var(--accent);
  }

  .messages {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    min-height: 0;
  }

  .bubble {
    padding: 0.5rem 0.6rem;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    line-height: 1.45;
    max-width: 95%;
  }

  .bubble.user {
    align-self: flex-end;
    background: var(--surface);
    border: 1px solid var(--border-subtle);
    color: var(--text);
  }

  .bubble.assistant {
    align-self: flex-start;
    background: transparent;
    color: var(--text-muted);
    padding-left: 0;
  }

  .bubble p {
    white-space: pre-wrap;
  }

  .link-btn {
    margin-top: 0.35rem;
    background: transparent;
    color: var(--accent);
    font-size: 0.65rem;
    padding: 0;
  }

  .top-actions {
    display: flex;
    justify-content: flex-end;
  }

  .thinking {
    font-size: 0.7rem;
    color: var(--text-faint);
  }

  .error {
    font-size: 0.7rem;
    color: var(--error);
  }

  .input-row {
    display: flex;
    gap: 0.35rem;
    align-items: center;
  }

  .input-row input {
    font-size: 0.75rem;
    padding: 0.45rem 0.55rem;
    flex: 1;
  }

  .input-row :global(.ui-btn.primary) {
    padding: 0.45rem 0.55rem;
    min-width: 36px;
  }
</style>