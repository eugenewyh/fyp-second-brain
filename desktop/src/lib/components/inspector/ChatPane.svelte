<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { research } from "$lib/stores/research.svelte";

  let message = $state("");

  async function send() {
    if (!message.trim()) return;
    await research.runQuickQuery(message);
    message = "";
    workspace.inspectorTab = "sources";
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
  <div class="messages placeholder">
    <p>Contextual AI chat — ask about the current note or vault.</p>
    <p class="hint">Uses Quick Query (RAG) for now; full chat in Phase 2.</p>
  </div>
  <div class="input-row">
    <input
      bind:value={message}
      placeholder="Ask about this note…"
      onkeydown={(e) => e.key === "Enter" && send()}
    />
    <button class="btn-primary" onclick={send} disabled={!connection.connected}>Send</button>
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
    color: var(--text-muted);
    overflow-y: auto;
  }

  .hint {
    margin-top: 0.5rem;
    font-size: 0.7rem;
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