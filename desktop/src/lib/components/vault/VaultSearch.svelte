<script lang="ts">
  import { workspace } from "$lib/stores/workspace.svelte";
  import SegmentedControl from "$lib/ui/SegmentedControl.svelte";

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
    placeholder="Search vault…"
    oninput={onInput}
  />
  <SegmentedControl
    options={[
      { value: "fuzzy", label: "Fuzzy" },
      { value: "semantic", label: "Semantic" },
    ]}
    bind:value={workspace.vaultSearchMode}
    onchange={onModeChange}
  />
</div>

<style>
  .vault-search {
    padding: 0.5rem 0.65rem;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .vault-search input {
    font-size: 0.75rem;
    padding: 0.4rem 0.55rem;
    background: var(--bg-elevated);
    border-color: var(--border-subtle);
  }
</style>