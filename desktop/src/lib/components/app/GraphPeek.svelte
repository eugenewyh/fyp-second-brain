<script lang="ts">
  import { X } from "@lucide/svelte";
  import DocumentView from "./DocumentView.svelte";
  import MetricChip from "$lib/ui/MetricChip.svelte";
  import type { VaultGraphNode } from "$lib/vault/vault-graph";
  import {
    confidenceTone,
    formatConfidence,
    groupPeekConnections,
    parsePeekMeta,
    peekConnectionRows,
    peekKindLabel,
    peekTypeLabel,
    type PeekNeighbor,
  } from "$lib/vault/graph-peek";

  interface Props {
    selected: VaultGraphNode;
    neighbors: PeekNeighbor[];
    body?: string;
    onSelect: (node: VaultGraphNode) => void;
    onClose: () => void;
    onAsk: (title: string) => void;
  }

  let { selected, neighbors, body = "", onSelect, onClose, onAsk }: Props = $props();

  const grouped = $derived(groupPeekConnections(neighbors));
  const connectionRows = $derived(peekConnectionRows(grouped));
  const meta = $derived(parsePeekMeta(body, selected.label));
  const typeLabel = $derived(peekTypeLabel(selected.type, selected.id));
  const isTopic = $derived(selected.type === "topic");

  function openSource(url: string) {
    if (typeof window !== "undefined") window.open(url, "_blank", "noopener");
  }
</script>

<aside class="peek" aria-label="Note and connections" data-testid="graph-peek">
  <header class="head">
    <div class="titles">
      <span class="type">{typeLabel}</span>
      <h2 class="title" title={selected.label}>{meta.title}</h2>
    </div>
    <button
      type="button"
      class="ask"
      onclick={() => onAsk(meta.title)}
    >
      Ask
    </button>
    <button
      type="button"
      class="icon-btn"
      title="Close"
      aria-label="Close peek"
      onclick={onClose}
    >
      <X size={16} />
    </button>
  </header>

  {#if grouped.topics.length > 0}
    <nav class="crumbs" aria-label="Topics">
      {#each grouped.topics as row, i (row.node.id)}
        {#if i > 0}
          <span class="sep" aria-hidden="true">›</span>
        {/if}
        <button type="button" class="crumb" onclick={() => onSelect(row.node)}>
          {row.node.label}
        </button>
      {/each}
    </nav>
  {/if}

  {#if meta.confidence != null || meta.sourceUrl}
    <div class="meta">
      {#if meta.confidence != null}
        <MetricChip
          label="Confidence"
          value={formatConfidence(meta.confidence)}
          tone={confidenceTone(meta.confidence)}
        />
      {/if}
      {#if meta.sourceUrl}
        <button
          type="button"
          class="source"
          title={meta.sourceUrl}
          onclick={() => openSource(meta.sourceUrl!)}
        >
          {meta.sourceUrl.replace(/^https?:\/\//i, "")}
        </button>
      {/if}
    </div>
  {/if}

  {#if !isTopic}
    <div class="doc">
      <DocumentView peek chrome={false} compact />
    </div>
  {:else if grouped.members.length > 0}
    <ul class="members" aria-label="Notes in this topic">
      {#each grouped.members as row (row.node.id)}
        <li>
          <button type="button" class="member" onclick={() => onSelect(row.node)}>
            <span class="member-kind">{peekTypeLabel(row.node.type, row.node.id)}</span>
            <span class="member-name">{row.node.label}</span>
          </button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty">No notes in this topic yet.</p>
  {/if}

  {#if connectionRows.length > 0}
    <section class="connected" aria-label="Connected notes">
      <h3 class="connected-label">
        Connected · {connectionRows.length}
      </h3>
      <ul class="conn-list">
        {#each connectionRows as row (row.node.id)}
          <li>
            <button type="button" class="conn" onclick={() => onSelect(row.node)}>
              <span class="kind">{peekKindLabel(row.kind)}</span>
              <span class="name">{row.node.label}</span>
            </button>
          </li>
        {/each}
      </ul>
    </section>
  {/if}
</aside>

<style>
  .peek {
    flex: 1.05 1 0;
    min-width: 20rem;
    max-width: 28rem;
    border-left: 1px solid var(--border-subtle);
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }

  .head {
    flex-shrink: 0;
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    padding: 0.55rem 0.5rem 0.35rem 0.9rem;
  }

  .titles {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.12rem;
  }

  .type {
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .title {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    line-height: 1.35;
    color: var(--text);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .ask {
    flex-shrink: 0;
    margin-top: 0.05rem;
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    padding: 0.2rem 0.35rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .ask:hover {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    margin-top: 0.05rem;
    flex-shrink: 0;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
  }

  .icon-btn:hover {
    color: var(--text);
    background: var(--chrome-action-hover);
  }

  .crumbs {
    flex-shrink: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.2rem 0.15rem;
    padding: 0 0.9rem 0.45rem;
  }

  .crumb {
    border: none;
    background: none;
    padding: 0;
    color: var(--text-muted);
    font-size: var(--text-xs);
    cursor: pointer;
    max-width: 9rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .crumb:hover {
    color: var(--text);
  }

  .sep {
    color: var(--text-faint);
    font-size: var(--text-xs);
    padding: 0 0.1rem;
  }

  .meta {
    flex-shrink: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.45rem;
    padding: 0 0.9rem 0.55rem;
  }

  .source {
    min-width: 0;
    flex: 1 1 8rem;
    border: none;
    background: transparent;
    padding: 0;
    text-align: left;
    color: var(--accent-link);
    font-size: var(--text-xs);
    text-decoration: underline;
    text-underline-offset: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }

  .source:hover {
    color: var(--text);
  }

  .doc {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border-top: 1px solid var(--border-subtle);
  }

  .doc :global(.document) {
    flex: 1;
    min-height: 0;
  }

  .members {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 0.35rem 0.45rem 0.75rem;
    border-top: 1px solid var(--border-subtle);
  }

  .member {
    width: 100%;
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    text-align: left;
    border: none;
    background: transparent;
    color: var(--text);
    padding: 0.4rem 0.45rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .member:hover {
    background: var(--chrome-action-hover);
  }

  .member-kind {
    flex-shrink: 0;
    width: 4.5rem;
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .member-name {
    min-width: 0;
    font-size: var(--text-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty {
    margin: auto;
    padding: 1.5rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .connected {
    flex-shrink: 0;
    max-height: 11rem;
    overflow-y: auto;
    border-top: 1px solid var(--border-subtle);
    padding: 0.55rem 0.55rem 0.7rem;
  }

  .connected-label {
    margin: 0 0.35rem 0.3rem;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .conn-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .conn {
    width: 100%;
    display: flex;
    align-items: baseline;
    gap: 0.55rem;
    text-align: left;
    border: none;
    background: transparent;
    padding: 0.32rem 0.35rem;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .conn:hover {
    background: var(--chrome-action-hover);
  }

  .kind {
    flex-shrink: 0;
    width: 5.25rem;
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .name {
    min-width: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .conn:hover .name {
    color: var(--text);
  }
</style>
