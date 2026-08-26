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
    <p class="sub">{hero.sub}</p>
  </header>

  {#if showSetup}
    <section class="setup" aria-label="Setup">
      <span class="setup-label">Setup</span>
      <div class="setup-row">
        {#each setupItems as item (item.id)}
          {#if item.action}
            <button
              type="button"
              class="setup-chip"
              onclick={() => runSetup(item.action)}
            >
              <span class="setup-dot" aria-hidden="true"></span>
              {item.label}
            </button>
          {:else}
            <span class="setup-chip static" role="status">
              <span class="setup-dot" aria-hidden="true"></span>
              {item.label}
            </span>
          {/if}
        {/each}
      </div>
    </section>
  {/if}

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
      Memory search blocked — fix embeddings, then re-ingest.
    {:else if phase === "bootstrap"}
      Setup first — chat needs a workspace and something to remember.
    {:else if phase === "seed"}
      <kbd>⌘K</kbd> commands · ingest or attach files · then ask and research unlock
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

  .setup {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.45rem 0.65rem;
    padding: 0.55rem 0.65rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--control-fill);
  }

  .setup-label {
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .setup-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .setup-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.55rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-full);
    background: var(--bg-elevated);
    color: var(--text);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .setup-chip.static {
    cursor: default;
    color: var(--text-muted);
  }

  .setup-chip:hover:not(.static) {
    border-color: var(--border);
    color: var(--text);
  }

  .setup-dot {
    width: 0.4rem;
    height: 0.4rem;
    border-radius: 50%;
    background: var(--warning);
    flex-shrink: 0;
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
