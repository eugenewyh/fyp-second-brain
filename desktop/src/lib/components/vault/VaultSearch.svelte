<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import Tooltip from "$lib/ui/Tooltip.svelte";

  interface Props {
    onSearch?: (query: string) => void;
  }

  let { onSearch }: Props = $props();

  function onInput() {
    onSearch?.(workspace.vaultSearchQuery);
  }

  function onModeChange(mode: string) {
    workspace.vaultSearchMode = mode as "fuzzy" | "semantic";
    onSearch?.(workspace.vaultSearchQuery);
  }
</script>

<div class="vault-search">
  <input
    data-vault-search
    bind:value={workspace.vaultSearchQuery}
    placeholder="Search library…"
    oninput={onInput}
  />
  <div class="mode-toggle">
    <Tooltip text="Match file names and paths">
      <button
        type="button"
        class="mode-btn"
        class:active={workspace.vaultSearchMode === "fuzzy"}
        data-testid="fuzzy-search"
        onclick={() => onModeChange("fuzzy")}
      >
        By name
      </button>
    </Tooltip>
    <Tooltip text="Find notes by meaning (requires connection)">
      <button
        type="button"
        class="mode-btn"
        class:active={workspace.vaultSearchMode === "semantic"}
        data-testid="semantic-search"
        onclick={() => onModeChange("semantic")}
      >
        By meaning
      </button>
    </Tooltip>
  </div>
  <button
    type="button"
    class="full-search"
    onclick={() => workspace.openCommandPalette()}
  >
    Full search <span class="ui-kbd">⌘K</span>
  </button>
</div>

<style>
  .mode-toggle {
    display: flex;
    gap: 2px;
    padding: 2px;
    background: var(--bg);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius);
  }

  .mode-btn {
    flex: 1;
    padding: 0.35rem 0.45rem;
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    background: transparent;
    color: var(--text-faint);
    border-radius: var(--radius-sm);
    border: none;
  }

  .mode-btn.active {
    background: var(--surface);
    color: var(--text);
  }

  .vault-search {
    padding: 0.55rem 0.7rem;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .full-search {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.3rem 0.15rem;
    background: transparent;
    color: var(--text-faint);
    font-size: var(--text-xs);
  }

  .full-search:hover {
    color: var(--text-muted);
  }
</style>
