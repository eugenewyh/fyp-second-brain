<script lang="ts">
  import { DEFAULT_SESSION_TITLE } from "$lib/stores/session-title";

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
</script>

<header class="chat-header" data-tauri-drag-region>
  <div class="header-title" class:muted>
    <span class="channel">{title}</span>
  </div>

  {#if remembered > 0}
    <div class="header-actions" data-tauri-drag-region="false">
      <span class="remember-chip">Remembers {remembered}</span>
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
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--border-subtle);
    color: var(--text-muted);
  }
</style>
