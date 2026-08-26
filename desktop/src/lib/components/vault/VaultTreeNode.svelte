<script lang="ts">
  import { slide } from "svelte/transition";
  import { cubicOut } from "svelte/easing";
  import type { VaultNode } from "$lib/vault/types";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import VaultTreeNode from "./VaultTreeNode.svelte";
  import { Folder, FolderOpen, FileText, FileType, ChevronRight } from "@lucide/svelte";

  interface Props {
    node: VaultNode;
    depth?: number;
    filter?: string;
  }

  let { node, depth = 0, filter = "" }: Props = $props();
  let expanded = $state(true);

  const expandTransition = { duration: 220, easing: cubicOut };

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
        <span class="chevron" class:open={expanded}>
          <ChevronRight size={12} strokeWidth={2} />
        </span>
        <span class="folder-icon" class:open={expanded} aria-hidden="true">
          <span class="folder-face closed">
            <Folder size={18} strokeWidth={1.75} />
          </span>
          <span class="folder-face opened">
            <FolderOpen size={18} strokeWidth={1.75} />
          </span>
        </span>
        <span class="name">{node.name}</span>
      </button>
      {#if expanded && node.children}
        <div class="tree-children" transition:slide={expandTransition}>
          {#each node.children as child (child.path)}
            <VaultTreeNode node={child} depth={depth + 1} {filter} />
          {/each}
        </div>
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
      <Icon size={18} strokeWidth={1.75} />
      <span class="name">{node.name}</span>
    </button>
  </div>
{/if}

<style>
  .tree-item {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    padding: 0.35rem 0.45rem;
    background: transparent;
    color: var(--text-muted);
    text-align: left;
    font-size: var(--text-sm);
    border-radius: var(--radius-sm);
    border: none;
    transition:
      background var(--dur-control) var(--ease-out),
      color var(--dur-control) var(--ease-out);
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
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 0.85rem;
    color: var(--text-faint);
    flex-shrink: 0;
    transition: transform var(--dur-expand) var(--ease-out);
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .folder-icon {
    position: relative;
    display: inline-flex;
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }

  .folder-face {
    position: absolute;
    inset: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition:
      opacity var(--dur-expand) var(--ease-out),
      transform var(--dur-expand) var(--ease-out);
  }

  .folder-face.closed {
    opacity: 1;
    transform: scale(1) rotate(0deg);
  }

  .folder-face.opened {
    opacity: 0;
    transform: scale(0.72) rotate(-8deg);
  }

  .folder-icon.open .folder-face.closed {
    opacity: 0;
    transform: scale(0.72) rotate(8deg);
  }

  .folder-icon.open .folder-face.opened {
    opacity: 1;
    transform: scale(1) rotate(0deg);
  }

  .tree-children {
    overflow: hidden;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>