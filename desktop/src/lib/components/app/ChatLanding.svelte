<script lang="ts">
  import type { Snippet } from "svelte";
  import {
    CHAT_STARTERS,
    chatSetupItems,
    chatStarterPrompt,
    landingHero,
    visibleStarterIds,
    type ChatStarterId,
    type ChatSetupAction,
    type LandingPhase,
  } from "$lib/assistant/chat-starters";

  interface Props {
    phase: LandingPhase;
    topicLabel: string;
    offline?: boolean;
    aiConfigured?: boolean;
    hasWorkspace?: boolean;
    libraryReady?: boolean;
    channelEmpty?: boolean;
    memoryBlocked?: boolean;
    disabled?: boolean;
    compose?: Snippet;
    onStarter?: (prompt: string, id: ChatStarterId) => void;
    onSetupAction?: (action: ChatSetupAction) => void;
    onNewWorkspace?: () => void;
  }

  let {
    phase,
    topicLabel,
    offline = false,
    aiConfigured = true,
    hasWorkspace = true,
    libraryReady = true,
    channelEmpty = false,
    memoryBlocked = false,
    disabled = false,
    compose,
    onStarter,
    onSetupAction,
    onNewWorkspace,
  }: Props = $props();

  let activeStarter = $state<ChatStarterId>("teach");

  const hero = $derived(landingHero(phase));
  const starterIds = $derived(visibleStarterIds(phase));
  const starters = $derived(CHAT_STARTERS.filter((s) => starterIds.includes(s.id)));
  const setupItems = $derived(
    chatSetupItems({
      offline,
      aiConfigured,
      hasWorkspace,
      libraryReady,
      channelEmpty,
      memoryBlocked,
    }),
  );
  const showSetup = $derived(setupItems.length > 0);
  const showCompose = $derived(phase !== "bootstrap" && !!compose);
  const showStarters = $derived(starters.length > 0);

  function pickStarter(id: ChatStarterId) {
    activeStarter = id;
    const prompt = chatStarterPrompt(id, topicLabel);
    onStarter?.(prompt, id);
  }

  function runSetup(action: ChatSetupAction | undefined) {
    if (action === "workspace") {
      onNewWorkspace?.();
      return;
    }
    if (action) onSetupAction?.(action);
  }
</script>

<div class="chat-landing" data-testid="chat-landing" data-phase={phase}>
  <header class="hero">
    <p class="kicker">{hero.kicker}</p>
    <h1 class="title">{hero.title}</h1>
    <p class="sub">
      {hero.sub}
      {#if showSetup}
        {#each setupItems as item, i (item.id)}
          {#if i === 0}<span class="setup-sep" aria-hidden="true"> </span>{/if}
          {#if item.action}
            <button
              type="button"
              class="setup-link"
              onclick={() => runSetup(item.action)}
            >
              {item.label}
            </button>
          {:else}
            <span class="setup-status" role="status">{item.label}</span>
          {/if}
          {#if i < setupItems.length - 1}<span class="setup-sep"> · </span>{/if}
        {/each}
      {/if}
    </p>
  </header>

  {#if phase === "bootstrap" && !hasWorkspace}
    <button type="button" class="primary-cta" onclick={() => onNewWorkspace?.()}>
      Create workspace
    </button>
  {/if}

  {#if showCompose}
    <div class="compose">
      {@render compose()}
    </div>
  {/if}

  {#if showStarters}
    <section class="starters" aria-label="Try next">
      <p class="starters-label">
        {phase === "seed" ? "Start here" : "Try next"}
      </p>
      <div class="starter-grid" class:single={starters.length === 1}>
        {#each starters as starter (starter.id)}
          <button
            type="button"
            class="starter"
            class:on={activeStarter === starter.id}
            disabled={disabled}
            data-testid={`starter-${starter.id}`}
            onclick={() => pickStarter(starter.id)}
          >
            <span class="starter-verb">{starter.verb}</span>
            <span class="starter-title">{starter.title}</span>
            <span class="starter-blurb">{starter.blurb}</span>
          </button>
        {/each}
      </div>
    </section>
  {/if}

  <p class="foot-hint">
    {#if offline}
      Backend offline — reconnect to send.
    {:else if memoryBlocked}
      Rebuilding search index when needed — wait a moment, or retry from the banner.
    {:else if phase === "bootstrap"}
      Setup first — chat needs a workspace and something to remember.
    {:else if phase === "seed"}
      <kbd>⌘K</kbd> commands · import folders or type a dump in the composer
    {:else}
      <kbd>⌘K</kbd> commands · autonomous agents write back to memory
    {/if}
  </p>
</div>

<style>
  .chat-landing {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;
  }

  .hero {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .kicker {
    margin: 0;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .title {
    margin: 0;
    font-size: clamp(1.25rem, 2.4vw, 1.55rem);
    font-weight: var(--font-semibold);
    letter-spacing: -0.03em;
    line-height: 1.22;
    color: var(--text);
  }

  .sub {
    margin: 0;
    max-width: 34rem;
    font-size: var(--text-sm);
    line-height: 1.55;
    color: var(--text-muted);
  }

  .setup-sep {
    color: var(--text-muted);
  }

  .setup-link {
    padding: 0;
    border: none;
    border-radius: 0;
    background: none;
    color: var(--text);
    font: inherit;
    font-weight: var(--font-medium);
    line-height: inherit;
    text-decoration: underline;
    text-underline-offset: 0.18em;
    text-decoration-color: color-mix(in srgb, var(--text) 35%, transparent);
    cursor: pointer;
    min-height: auto;
  }

  .setup-link:hover {
    text-decoration-color: var(--text);
  }

  .setup-status {
    font: inherit;
    color: var(--text-muted);
  }

  .primary-cta {
    align-self: flex-start;
    padding: 0.55rem 0.95rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--text);
    color: var(--bg);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .primary-cta:hover {
    opacity: 0.92;
  }

  .compose {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .starters-label {
    margin: 0 0 0.45rem;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .starter-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .starter-grid.single {
    grid-template-columns: 1fr;
    max-width: 18rem;
  }

  .starter {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
    padding: 0.65rem 0.7rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: transparent;
    text-align: left;
    cursor: pointer;
    min-height: auto;
    transition:
      border-color 0.12s ease,
      background 0.12s ease;
  }

  .starter:hover:not(:disabled),
  .starter.on {
    background: var(--control-fill);
    border-color: var(--border);
  }

  .starter:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .starter-verb {
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .starter-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text);
    letter-spacing: -0.01em;
  }

  .starter-blurb {
    font-size: var(--text-xs);
    line-height: 1.4;
    color: var(--text-muted);
  }

  .foot-hint {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--text-faint);
  }

  .foot-hint kbd {
    font-family: var(--font-mono);
    font-size: 0.95em;
    padding: 0.05rem 0.3rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
    background: var(--control-fill);
    color: var(--text-muted);
  }

  @media (max-width: 720px) {
    .starter-grid:not(.single) {
      grid-template-columns: 1fr;
    }
  }
</style>
