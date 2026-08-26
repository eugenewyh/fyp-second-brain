<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    effectiveThemeDescription,
    themePreferenceLabel,
    type ThemePreference,
  } from "$lib/theme/theme-prefs";
  import { THEME_CHANGE_EVENT } from "$lib/theme/apply-theme";
  import {
    getEffectiveTheme,
    getThemePreference,
    setThemePreference,
  } from "$lib/theme/init-theme";

  const OPTIONS: ThemePreference[] = ["light", "dark", "system"];

  let preference = $state<ThemePreference>("system");
  let effective = $state<"light" | "dark">("light");

  function syncFromStore() {
    preference = getThemePreference();
    effective = getEffectiveTheme();
  }

  function select(next: ThemePreference) {
    setThemePreference(next);
    syncFromStore();
  }

  onMount(() => {
    syncFromStore();
    window.addEventListener(THEME_CHANGE_EVENT, syncFromStore);
  });

  onDestroy(() => {
    window.removeEventListener(THEME_CHANGE_EVENT, syncFromStore);
  });
</script>

<section class="st-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Color theme</h3>
    <p class="st-card-sub">Choose light, dark, or match your system setting.</p>
  </div>

  <div class="theme-segment" role="radiogroup" aria-label="Color theme">
    {#each OPTIONS as option}
      <button
        type="button"
        class="theme-segment-btn"
        class:active={preference === option}
        role="radio"
        aria-checked={preference === option}
        onclick={() => select(option)}
      >
        {themePreferenceLabel(option)}
      </button>
    {/each}
  </div>

  <p class="theme-hint">{effectiveThemeDescription(preference, effective)}</p>
</section>

<style>
  .theme-segment {
    display: inline-flex;
    gap: 0.15rem;
    padding: 0.15rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-subtle);
    background: var(--control-fill);
  }

  .theme-segment-btn {
    border: none;
    background: transparent;
    color: var(--text-muted);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    padding: 0.35rem 0.75rem;
    border-radius: var(--radius-md);
    cursor: pointer;
    min-width: 4.5rem;
  }

  .theme-segment-btn:hover {
    color: var(--text);
    background: var(--surface-hover);
  }

  .theme-segment-btn.active {
    color: var(--text);
    background: var(--paper);
    box-shadow: var(--shadow-md);
  }

  .theme-hint {
    margin: 0.65rem 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }
</style>
