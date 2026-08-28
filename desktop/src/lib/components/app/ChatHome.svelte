<script lang="ts">
  import { assistant } from "$lib/stores/assistant.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import AgentPane from "./AgentPane.svelte";
  import ChatHeader from "./ChatHeader.svelte";
  import DocumentView from "./DocumentView.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { DEFAULT_SESSION_TITLE } from "$lib/stores/session-title";
  import PaneResizer from "$lib/components/workspace/PaneResizer.svelte";
  import {
    clampPeekWidth,
    loadPeekWidth,
    savePeekWidth,
  } from "$lib/workspace/layout-prefs";

  const showDocPeek = $derived(app.isDocumentPeek && app.isHome);
  const unboundChat = $derived(!workspace.activeTopicPath);
  const chatTitle = $derived(assistant.activeSession?.title ?? DEFAULT_SESSION_TITLE);
  const remembered = $derived.by(() => {
    let n = 0;
    for (const t of assistant.getActiveThread()) {
      if (t.kind === "digest" && t.status === "done") {
        n += (t.claimsCreated ?? 0) + (t.claimsRevised ?? 0);
      }
      if (t.kind === "research" && t.status === "done") {
        n += t.claimCount ?? 0;
      }
    }
    return n;
  });

  let peekWidth = $state(loadPeekWidth());

  function onPeekResize(delta: number) {
    // Resizer sits left of peek: drag right shrinks the document pane.
    peekWidth = clampPeekWidth(peekWidth - delta);
  }

  function onPeekResizeEnd() {
    savePeekWidth(peekWidth);
  }

  $effect(() => {
    if (!app.isDocumentPeek) return;
    if (assistant.inspectorOpen) assistant.inspectorOpen = false;
  });

  $effect(() => {
    void assistant.activeSessionId;
    assistant.ensureManagerOpener(workspace.channelEmpty);
  });

  $effect(() => {
    const path = workspace.activeTopicPath;
    if (!path || !app.isHome) return;
    void assistant.ensureUnfiledNotesRemembered(path);
  });
</script>

<div class="chat-home">
  <div class="thread-col">
    <ChatHeader
      chatTitle={chatTitle}
      remembered={remembered}
      unbound={unboundChat}
    />
    <AgentPane />
  </div>
  {#if showDocPeek}
    <PaneResizer
      onResize={onPeekResize}
      onResizeEnd={onPeekResizeEnd}
      testId="splitter-peek"
    />
    <aside class="peek-pane" style="width: {peekWidth}px" aria-label="Document">
      <DocumentView peek />
    </aside>
  {/if}
</div>

<style>
  .chat-home {
    display: flex;
    height: 100%;
    min-height: 0;
    background: var(--bg);
  }
  .thread-col {
    flex: 1;
    min-width: 18rem;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }
  .thread-col :global(.agent-pane) {
    flex: 1;
    min-height: 0;
  }
  .peek-pane {
    flex-shrink: 0;
    border-left: 1px solid var(--border-subtle);
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }

  .peek-pane :global(.document) {
    flex: 1;
    min-height: 0;
  }
</style>
