<script lang="ts">
  import type { VaultNode } from "$lib/vault/types";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import VaultTreeNode from "./VaultTreeNode.svelte";

  interface Props {
    node: VaultNode;
    depth?: number;
    filter?: string;
  }

  let { node, depth = 0, filter = "" }: Props = $props();
  let expanded = $state(true);

  function matchesFilter(name: string): boolean {
    if (!filter.trim()) return true;
    return name.toLowerCase().includes(filter.toLowerCase());
  }

  function openFile() {
    if (node.type === "file" && node.name.endsWith(".md")) {
      tabs.openNoteTab(node.path, node.name);
      workspace.setActiveNote(node.path);
    }
  }
</script>

{#if node.type === "folder"}
  {#if !filter.trim() || node.children?.some((c) => matchesFilter(c.name))}
    <div style="padding-left: {depth * 0.75}rem">
      <button class="tree-item folder" onclick={() => (expanded = !expanded)}>
        <span class="chevron" class:open={expanded}>▸</span>
        <span class="icon">📁</span>
        {node.name}
      </button>
      {#if expanded && node.children}
        {#each node.children as child (child.path)}
          <VaultTreeNode node={child} depth={depth + 1} {filter} />
        {/each}
      {/if}
    </div>
  {/if}
{:else if matchesFilter(node.name)}
  <div style="padding-left: {depth * 0.75}rem">
    <button
      class="tree-item file"
      class:active={workspace.activeNotePath === node.path}
      onclick={openFile}
    >
      <span class="icon">📄</span>
      {node.name}
    </button>
  </div>
{/if}

<style>
  .tree-item {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    width: 100%;
    padding: 0.35rem 0.5rem;
    background: transparent;
    color: var(--text-muted);
    text-align: left;
    font-size: 0.8rem;
    border-radius: 6px;
  }

  .tree-item:hover {
    background: var(--surface-hover);
    color: var(--text);
  }

  .tree-item.active {
    background: var(--accent);
    color: white;
  }

  .chevron {
    font-size: 0.65rem;
    width: 0.75rem;
    transition: transform 0.15s;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .icon {
    font-size: 0.75rem;
  }
</style>