<script lang="ts">
  import type { VaultNode } from "$lib/vault/types";
  import VaultTreeNode from "./VaultTreeNode.svelte";

  interface Props {
    nodes: VaultNode[];
    filter?: string;
  }

  let { nodes, filter = "" }: Props = $props();
</script>

<div class="tree-root">
  {#each nodes as node (node.path)}
    <VaultTreeNode {node} {filter} />
  {/each}
</div>