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

<div class="backlinks" data-testid="backlinks-section">
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

  <h4>Similar notes</h4>
  {#if loading}
    <p class="hint">Finding related notes…</p>
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
    <p class="hint">Open a note to see similar notes in your library</p>
  {/if}
</div>

<style>
  .backlinks {
    padding: 0.75rem;
    font-size: var(--text-sm);
    overflow-y: auto;
    height: 100%;
  }

  h4 {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    font-weight: var(--font-semibold);
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
    font-size: var(--text-md);
    text-align: left;
  }

  button:hover {
    color: var(--accent);
  }

  .excerpt {
    font-size: var(--text-xs);
    color: var(--text-muted);
    margin-top: 0.2rem;
  }

  .hint {
    color: var(--text-muted);
    font-size: var(--text-sm);
  }
</style>