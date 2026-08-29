<script lang="ts">
  import { DEFAULT_SESSION_TITLE } from "$lib/stores/session-title";
  import { app } from "$lib/stores/app.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";

  interface Props {
    chatTitle?: string | null;
    remembered?: number;
    unbound?: boolean;
  }

  let {
    chatTitle = null,
    remembered = 0,
    unbound = false,
  }: Props = $props();

  const title = $derived(chatTitle?.trim() || DEFAULT_SESSION_TITLE);

  const muted = $derived(
    unbound || !chatTitle?.trim() || chatTitle.trim() === DEFAULT_SESSION_TITLE,
  );

  function openMemoryForChat() {
    const path = assistant.activeProjectPath();
    app.openMemory({ topicPath: path });
    if (path) workspace.setActiveTopic(path);
  }
</script>

<header class="chat-header" data-tauri-drag-region>
  <div class="header-title" class:muted>
    <span class="channel">{title}</span>
  </div>

  {#if remembered > 0}
    <div class="header-actions" data-tauri-drag-region="false">
      <button
        type="button"
        class="remember-chip"
        title="Open Memory for this topic"
        data-testid="header-memory"
        onclick={openMemoryForChat}
      >
        Remembers {remembered}
      </button>
    </div>
  {/if}
</header>

<style>
  .chat-header {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    min-height: var(--titlebar-height);
    padding: 0 1rem;
    position: relative;
    z-index: 5;
    background: var(--bg);
    border-bottom: 1px solid var(--border-subtle);
    -webkit-app-region: drag;
    app-region: drag;
  }

  .header-title {
    min-width: 0;
    flex: 1;
    display: flex;
    align-items: center;
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
    line-height: 1.3;
    letter-spacing: -0.01em;
  }

  .header-title.muted {
    color: var(--text-muted);
  }

  .channel {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-shrink: 0;
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .remember-chip {
    display: inline-flex;
    align-items: center;
    height: 26px;
    padding: 0 0.6rem;
    border: 1px solid color-mix(in srgb, var(--warning) 35%, var(--border));
    border-radius: var(--radius-full);
    background: var(--warning-dim);
    color: var(--text);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .remember-chip:hover {
    border-color: color-mix(in srgb, var(--warning) 55%, var(--border));
    background: color-mix(in srgb, var(--warning) 18%, transparent);
  }
</style>
