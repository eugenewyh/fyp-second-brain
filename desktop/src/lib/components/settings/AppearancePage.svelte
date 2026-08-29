<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import {
    effectiveThemeDescription,
    themePreferenceLabel,
    type PaletteId,
    type ThemePreference,
  } from "$lib/theme/theme-prefs";
  import { PALETTES } from "$lib/theme/palette-registry";
  import { THEME_CHANGE_EVENT } from "$lib/theme/apply-theme";
  import {
    getEffectiveTheme,
    getPalettePreference,
    getThemePreference,
    setPalettePreference,
    setThemePreference,
  } from "$lib/theme/init-theme";

  const MODE_OPTIONS: ThemePreference[] = ["light", "dark", "system"];

  let preference = $state<ThemePreference>("system");
  let palette = $state<PaletteId>("nous");
  let effective = $state<"light" | "dark">("light");

  function syncFromStore() {
    preference = getThemePreference();
    palette = getPalettePreference();
    effective = getEffectiveTheme();
  }

  function selectMode(next: ThemePreference) {
    setThemePreference(next);
    syncFromStore();
  }

  function selectPalette(next: PaletteId) {
    setPalettePreference(next);
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
    <h3 class="st-card-title">Theme</h3>
    <p class="st-card-sub">Desktop palettes only. The selected mode is applied on top.</p>
  </div>

  <div class="mode-segment" role="radiogroup" aria-label="Color mode">
    {#each MODE_OPTIONS as option}
      <button
        type="button"
        class="mode-segment-btn"
        class:active={preference === option}
        role="radio"
        aria-checked={preference === option}
        onclick={() => selectMode(option)}
      >
        {themePreferenceLabel(option)}
      </button>
    {/each}
  </div>

  <p class="mode-hint">{effectiveThemeDescription(preference, effective)}</p>
</section>

<section class="st-card palette-card">
  <div class="st-card-head">
    <h3 class="st-card-title">Palette</h3>
    <p class="st-card-sub">Choose a color personality for the app.</p>
  </div>

  <div class="palette-grid" role="radiogroup" aria-label="Color palette">
    {#each PALETTES as item (item.id)}
      <button
        type="button"
        class="palette-tile"
        class:selected={palette === item.id}
        role="radio"
        aria-checked={palette === item.id}
        aria-label={item.name}
        onclick={() => selectPalette(item.id)}
      >
        <div
          class="palette-preview"
          style:--preview-bg={item.preview.bg}
          style:--preview-accent={item.preview.accent}
          style:--preview-muted={item.preview.muted}
        >
          <span class="preview-sidebar"></span>
          <span class="preview-main">
            <span class="preview-line accent"></span>
            <span class="preview-line"></span>
            <span class="preview-line short"></span>
          </span>
        </div>
        <span class="palette-name">{item.name}</span>
        <span class="palette-desc">{item.description}</span>
      </button>
    {/each}
  </div>
</section>

<style>
  .mode-segment {
    display: inline-flex;
    gap: 0.15rem;
    padding: 0.15rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-subtle);
    background: var(--control-fill);
  }

  .mode-segment-btn {
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

  .mode-segment-btn:hover {
    color: var(--text);
    background: var(--surface-hover);
  }

  .mode-segment-btn.active {
    color: var(--text);
    background: var(--paper);
    box-shadow: var(--shadow-md);
  }

  .mode-hint {
    margin: 0.65rem 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .palette-card {
    margin-top: var(--space-4);
  }

  .palette-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3);
  }

  .palette-tile {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0.45rem;
    padding: 0.65rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    background: var(--paper);
    text-align: left;
    cursor: pointer;
    min-height: unset;
    transition:
      border-color var(--dur-control) var(--ease-out),
      box-shadow var(--dur-control) var(--ease-out);
  }

  .palette-tile:hover {
    border-color: var(--border-active);
    background: var(--paper);
  }

  .palette-tile.selected {
    border-color: var(--accent-live);
    box-shadow: 0 0 0 1px color-mix(in oklch, var(--accent-live) 35%, transparent);
  }

  .palette-preview {
    display: flex;
    gap: 0.35rem;
    height: 4.5rem;
    padding: 0.45rem;
    border-radius: var(--radius-md);
    background: var(--preview-bg);
    border: 1px solid color-mix(in oklch, var(--preview-muted) 80%, transparent);
    overflow: hidden;
  }

  .preview-sidebar {
    flex: 0 0 22%;
    border-radius: 3px;
    background: color-mix(in oklch, var(--preview-muted) 85%, var(--preview-bg));
  }

  .preview-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    justify-content: center;
    padding-right: 0.15rem;
  }

  .preview-line {
    display: block;
    height: 0.35rem;
    border-radius: 999px;
    background: color-mix(in oklch, var(--preview-muted) 70%, var(--preview-bg));
  }

  .preview-line.accent {
    width: 55%;
    background: var(--preview-accent);
  }

  .preview-line.short {
    width: 40%;
  }

  .palette-name {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text);
  }

  .palette-desc {
    font-size: var(--text-xs);
    line-height: 1.4;
    color: var(--text-muted);
  }
</style>
