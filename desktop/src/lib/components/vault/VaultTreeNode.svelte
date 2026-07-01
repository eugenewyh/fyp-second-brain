<script lang="ts">
  import type { VaultNode } from "$lib/vault/types";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import VaultTreeNode from "./VaultTreeNode.svelte";
  import { Folder, FileText, FileType } from "@lucide/svelte";

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
    if (node.type !== "file") return;
    tabs.openNoteTab(node.path, node.name);
    workspace.setActiveNote(node.path);
  }

  function fileIcon(name: string) {
    const lower = name.toLowerCase();
    if (lower.endsWith(".pdf")) return FileType;
    return FileText;
  }
</script>

{#if node.type === "folder"}
  {#if !filter.trim() || node.children?.some((c) => matchesFilter(c.name))}
    <div style="padding-left: {depth * 0.65}rem">
      <button class="tree-item folder" onclick={() => (expanded = !expanded)}>
        <span class="chevron" class:open={expanded}>▸</span>
        <Folder size={14} strokeWidth={1.75} />
        <span class="name">{node.name}</span>
      </button>
      {#if expanded && node.children}
        {#each node.children as child (child.path)}
          <VaultTreeNode node={child} depth={depth + 1} {filter} />
        {/each}
      {/if}
    </div>
  {/if}
{:else if matchesFilter(node.name)}
  {@const Icon = fileIcon(node.name)}
  <div style="padding-left: {depth * 0.65}rem">
    <button
      class="tree-item file"
      class:active={workspace.activeNotePath === node.path}
      onclick={openFile}
    >
      <Icon size={14} strokeWidth={1.75} />
      <span class="name">{node.name}</span>
    </button>
  </div>
{/if}

<style>
  .tree-item {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    width: 100%;
    padding: 0.3rem 0.45rem;
    background: transparent;
    color: var(--text-muted);
    text-align: left;
    font-size: 0.75rem;
    border-radius: var(--radius-sm);
    border: none;
  }

  .tree-item:hover {
    background: var(--surface-hover);
    color: var(--text);
  }

  .tree-item.active {
    background: var(--surface-hover);
    color: var(--text);
    box-shadow: inset 2px 0 0 var(--accent);
  }

  .tree-item :global(svg) {
    flex-shrink: 0;
    color: var(--text-faint);
  }

  .tree-item.active :global(svg) {
    color: var(--text-muted);
  }

  .chevron {
    font-size: 0.6rem;
    width: 0.65rem;
    color: var(--text-faint);
    transition: transform 0.12s;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>