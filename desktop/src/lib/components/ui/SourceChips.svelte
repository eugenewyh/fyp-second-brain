<script lang="ts">
  import {
    classifySourceOrigin,
    originShort,
    sourceDisplayName,
  } from "$lib/vault/source-origin";

  interface Props {
    sources: { index?: number; source: string; page?: number | null }[];
    onOpen?: (path: string) => void;
  }

  let { sources, onOpen }: Props = $props();

  const grouped = $derived.by(() => {
    const map = new Map<string, { origin: string; label: string; items: string[] }>();
    for (const s of sources) {
      if (!s.source) continue;
      const origin = classifySourceOrigin(s.source);
      const key = origin;
      if (!map.has(key)) {
        map.set(key, { origin, label: originShort(origin), items: [] });
      }
      map.get(key)!.items.push(s.source);
    }
    return [...map.values()];
  });
</script>

{#if sources.length}
  <div class="sources" data-testid="source-origin-chips">
    <div class="chips">
      {#each grouped as g}
        <span class="chip" data-origin={g.origin}>{g.label} · {g.items.length}</span>
      {/each}
    </div>
    <ul class="list">
      {#each sources as s}
        {#if s.source}
          {@const origin = classifySourceOrigin(s.source)}
          <li>
            {#if onOpen && (origin === "personal" || origin === "past_research")}
              <button
                type="button"
                class="name"
                title={s.source}
                onclick={() => onOpen?.(s.source)}
              >
                {sourceDisplayName(s.source)}
              </button>
            {:else}
              <span class="name static" title={s.source}>{sourceDisplayName(s.source)}</span>
            {/if}
          </li>
        {/if}
      {/each}
    </ul>
  </div>
{/if}

<style>
  .sources {
    margin-top: 0.15rem;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0 0 0.45rem;
  }

  .chip {
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    color: var(--text-muted);
    background: var(--control-fill);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 0.2rem 0.5rem;
  }

  .list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    margin: 0;
    padding: 0;
  }

  li {
    min-width: 0;
    font-size: var(--text-sm);
  }

  .name {
    display: block;
    width: 100%;
    max-width: 100%;
    margin: 0;
    padding: 0.15rem 0;
    border: none;
    border-radius: 0;
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-normal);
    line-height: 1.4;
    text-align: left;
    text-decoration: none;
    min-height: auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }

  .name.static {
    cursor: default;
  }

  .name:hover:not(.static) {
    color: var(--text);
  }
</style>
