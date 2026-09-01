<script lang="ts">
  import { app } from "$lib/stores/app.svelte";
  import IngestPanel from "$lib/components/documents/IngestPanel.svelte";
  import SettingsPanel from "$lib/components/settings/SettingsPanel.svelte";
  import SourcesPane from "$lib/components/inspector/SourcesPane.svelte";
  import BacklinksPane from "$lib/components/inspector/BacklinksPane.svelte";
  import CapabilitiesView from "./CapabilitiesView.svelte";
  import ArtifactsView from "./ArtifactsView.svelte";

  const wide = $derived(
    app.sheet === "capabilities" ||
      app.sheet === "artifacts",
  );

  const title = $derived.by(() => {
    if (app.sheet === "ingest") return "Library";
    if (app.sheet === "settings") return "Settings";
    if (app.sheet === "references") return "References";
    if (app.sheet === "capabilities") return "Capabilities";
    if (app.sheet === "artifacts") return "Artifacts";
    return "";
  });
</script>

{#if app.sheet}
  <div
    class="overlay-backdrop sheet-backdrop"
    role="presentation"
    onclick={() => app.closeSheet()}
  >
    <div
      class="overlay-panel sheet"
      class:sheet-settings={app.sheet === "settings"}
      class:sheet-wide={wide}
      role="dialog"
      aria-label={title}
      onclick={(e) => e.stopPropagation()}
    >
      <header class="sheet-header" data-tauri-drag-region>
        <h2>{title}</h2>
        <button type="button" class="close" data-tauri-drag-region="false" onclick={() => app.closeSheet()}>Close</button>
      </header>
      <div
        class="sheet-body ui-scroll"
        class:sheet-body-flush={app.sheet === "settings" || app.sheet === "ingest" || wide}
      >
        {#if app.sheet === "ingest"}
          <IngestPanel />
        {:else if app.sheet === "settings"}
          <SettingsPanel />
        {:else if app.sheet === "references"}
          <div class="refs">
            <SourcesPane />
            <div class="sep"></div>
            <BacklinksPane />
          </div>
        {:else if app.sheet === "capabilities"}
          <CapabilitiesView />
        {:else if app.sheet === "artifacts"}
          <ArtifactsView />
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .sheet-backdrop {
    z-index: 1100;
  }

  .sheet {
    width: min(560px, 94vw);
    max-height: 86vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sheet.sheet-settings {
    width: min(860px, 94vw);
    height: min(720px, 86vh);
    max-height: 86vh;
  }

  .sheet.sheet-wide {
    width: min(960px, 94vw);
    height: min(820px, 90vh);
    max-height: 90vh;
  }

  .sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
    -webkit-app-region: drag;
    app-region: drag;
  }

  .sheet-header .close {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .sheet-header h2 {
    font-size: var(--text-lg);
    font-weight: var(--font-medium);
  }

  .close {
    background: transparent;
    color: var(--text-faint);
    font-size: var(--text-base);
    padding: 0;
  }

  .close:hover {
    color: var(--text);
  }

  .sheet-body {
    padding: 1rem;
    overflow-y: auto;
    flex: 1 1 auto;
    min-height: 0;
  }

  .sheet-body-flush {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .sheet-body-flush :global(.library) {
    height: 100%;
    overflow-y: auto;
  }

  .refs {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .sep {
    border-top: 1px solid var(--border-subtle);
  }
</style>
