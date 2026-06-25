<script lang="ts">
  import { api } from "$lib/api";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { loadVaultTree, readNote, getVaultRoot } from "$lib/vault/load";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import { splitFrontmatter } from "$lib/vault/markdown";
  import { backlinksForNote, buildBacklinkIndex } from "$lib/vault/backlinks";

  let related = $state<{ source: string; excerpt: string; distance?: number }[]>([]);
  let backlinkPaths = $state<string[]>([]);
  let loading = $state(false);

  async function loadLinks() {
    if (!workspace.activeNotePath) {
      related = [];
      backlinkPaths = [];
      return;
    }

    loading = true;
    try {
      const root = workspace.vaultRoot ?? (await getVaultRoot());
      const tree = await loadVaultTree(root);
      const files = flattenVaultFiles(tree);
      const bodies: Record<string, string> = {};
      await Promise.all(
        files
          .filter((f) => f.path.endsWith(".md"))
          .map(async (f) => {
            try {
              const raw = await readNote(f.path);
              bodies[f.path] = splitFrontmatter(raw).body;
            } catch {
              /* skip */
            }
          }),
      );
      const index = buildBacklinkIndex(files, bodies);
      backlinkPaths = backlinksForNote(workspace.activeNotePath, index);

      if (connection.connected) {
        const name = workspace.activeNotePath.split("/").pop() ?? "";
        const excerpt = bodies[workspace.activeNotePath]?.slice(0, 500) ?? name;
        const result = await api.vaultRelated(excerpt || name, 5);
        related = result.results;
      } else {
        related = [];
      }
    } catch {
      related = [];
      backlinkPaths = [];
    } finally {
      loading = false;
    }
  }

  function openPath(path: string) {
    tabs.openNoteTab(path);
    workspace.setActiveNote(path);
  }

  $effect(() => {
    workspace.activeNotePath;
    workspace.vaultRefreshNonce;
    if (workspace.activeNotePath) void loadLinks();
  });
</script>

<div class="backlinks">
  <h4>Wikilink backlinks</h4>
  {#if loading}
    <p class="hint">Scanning vault…</p>
  {:else if backlinkPaths.length}
    <ul>
      {#each backlinkPaths as path}
        <li>
          <button onclick={() => openPath(path)}>{path.split("/").pop()}</button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="hint">No notes link here yet</p>
  {/if}

  <h4>Embedding-related</h4>
  {#if loading}
    <p class="hint">Searching embeddings…</p>
  {:else if related.length}
    <ul>
      {#each related as item}
        <li>
          <button onclick={() => openPath(item.source)}>
            {item.source.split("/").pop()}
          </button>
          <p class="excerpt">{item.excerpt.slice(0, 120)}…</p>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="hint">Select a note to see Chroma-related chunks</p>
  {/if}
</div>

<style>
  .backlinks {
    padding: 0.75rem;
    font-size: 0.8rem;
    overflow-y: auto;
    height: 100%;
  }

  h4 {
    font-size: 0.75rem;
    color: var(--accent);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  h4:not(:first-child) {
    margin-top: 0.85rem;
  }

  ul {
    list-style: none;
  }

  li {
    margin-bottom: 0.65rem;
  }

  button {
    background: transparent;
    color: var(--text);
    padding: 0;
    font-size: 0.85rem;
    text-align: left;
  }

  button:hover {
    color: var(--accent);
  }

  .excerpt {
    font-size: 0.7rem;
    color: var(--text-muted);
    margin-top: 0.2rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.75rem;
  }
</style>