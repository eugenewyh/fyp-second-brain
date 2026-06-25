<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { chat } from "$lib/stores/chat.svelte";
  import { readNote } from "$lib/vault/load";
  import { splitFrontmatter } from "$lib/vault/markdown";

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
    Aware of:
    <strong>{workspace.activeNotePath?.split("/").pop() ?? "no note"}</strong>
    {#if workspace.selectedText}
      <span class="selection">+ selected text</span>
    {/if}
  </p>

  <div class="messages" aria-live="polite">
    {#if thread.length === 0}
      <p class="hint">Ask about the open note or your vault. Conversation stays in this thread.</p>
    {:else}
      {#each thread as turn}
        <div class="bubble" class:user={turn.role === "user"} class:assistant={turn.role === "assistant"}>
          <span class="role">{turn.role === "user" ? "You" : "Assistant"}</span>
          <p>{turn.content}</p>
          {#if turn.role === "assistant" && turn.sources?.length}
            <button class="link-btn" onclick={viewSources}>View sources ({turn.sources.length})</button>
          {/if}
        </div>
      {/each}
    {/if}
    {#if chat.loading}
      <p class="hint">Thinking…</p>
    {/if}
    {#if chat.error}
      <p class="error">{chat.error}</p>
    {/if}
  </div>

  <div class="actions">
    {#if thread.length}
      <button class="ghost" onclick={clearChat} disabled={chat.loading}>Clear</button>
    {/if}
  </div>

  <div class="input-row">
    <input
      bind:value={message}
      placeholder="Ask about this note…"
      onkeydown={(e) => e.key === "Enter" && send()}
      disabled={!connection.connected || chat.loading}
    />
    <button class="btn-primary" onclick={send} disabled={!connection.connected || chat.loading}>
      Send
    </button>
  </div>
</div>

<style>
  .chat-pane {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 0.75rem;
    gap: 0.5rem;
  }

  .context {
    font-size: 0.75rem;
    color: var(--text-muted);
  }

  .selection {
    color: var(--accent);
  }

  .messages {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem;
    font-size: 0.8rem;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .bubble {
    padding: 0.5rem 0.6rem;
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
  }

  .bubble.user {
    align-self: flex-end;
    max-width: 92%;
    border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
  }

  .bubble.assistant {
    align-self: flex-start;
    max-width: 92%;
  }

  .role {
    display: block;
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
  }

  .bubble p {
    white-space: pre-wrap;
    line-height: 1.45;
  }

  .link-btn,
  .ghost {
    margin-top: 0.35rem;
    background: transparent;
    color: var(--accent);
    font-size: 0.7rem;
    padding: 0;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.75rem;
  }

  .error {
    color: var(--error);
    font-size: 0.75rem;
  }

  .input-row {
    display: flex;
    gap: 0.4rem;
  }

  .input-row input {
    font-size: 0.8rem;
  }

  .input-row button {
    flex-shrink: 0;
    font-size: 0.8rem;
    padding: 0.45rem 0.7rem;
  }
</style>