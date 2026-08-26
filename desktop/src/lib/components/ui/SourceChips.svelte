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
  <div class="chips" data-testid="source-origin-chips">
    {#each grouped as g}
      <span class="chip" data-origin={g.origin}>{g.label} · {g.items.length}</span>
    {/each}
  </div>
  <ul class="list">
    {#each sources as s}
      {#if s.source}
        {@const origin = classifySourceOrigin(s.source)}
        <li>
          <span class="tag" data-origin={origin}>{originShort(origin)}</span>
          {#if onOpen && (origin === "personal" || origin === "past_research")}
            <button type="button" class="name" onclick={() => onOpen?.(s.source)}>
              {sourceDisplayName(s.source)}
            </button>
          {:else}
            <span class="name static">{sourceDisplayName(s.source)}</span>
          {/if}
        </li>
      {/if}
    {/each}
  </ul>
{/if}

<style>
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0.5rem 0 0.4rem;
  }

  .chip {
    font-size: var(--text-xs);
    color: var(--text-muted);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    padding: 0.15rem 0.5rem;
  }

  .list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    margin-top: 0.35rem;
  }

  li {
    display: flex;
    align-items: baseline;
    gap: 0.45rem;
    font-size: var(--text-xs);
  }

  .tag {
    flex-shrink: 0;
    color: var(--text-faint);
    min-width: 4.5rem;
  }

  .name {
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-xs);
    font-weight: var(--font-normal);
    padding: 0;
    min-height: auto;
    text-align: left;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .name.static {
    text-decoration: none;
  }

  .name:hover {
    color: var(--text);
  }
</style>
