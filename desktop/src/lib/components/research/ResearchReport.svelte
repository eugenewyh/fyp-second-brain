<script lang="ts">
  import type { ResearchResult } from "$lib/api";
  import {
    displayReportTitle,
    isFindingsSectionTitle,
    isLeadSectionTitle,
    parseReportSections,
    parseSourcesSection,
    renderSectionBody,
    type ReportSection,
  } from "$lib/research/render";
  import { formatRetrievalSummary } from "$lib/assistant/transparency";
  import { saveResearchAsNote } from "$lib/vault/notes";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { classifySourceOrigin } from "$lib/vault/source-origin";
  import { resolveSourcePath } from "$lib/vault/source-path";
  import { flattenVaultFiles } from "$lib/vault/flatten";
  import { getVaultRoot, loadVaultTree } from "$lib/vault/load";
  import type { VaultFileRef } from "$lib/vault/flatten";

  interface Props {
    result: ResearchResult;
    /** Hide document toolbar when parent already shows actions */
    hideToolbar?: boolean;
    /** Thread: unbubbled answer prose (no TOC, toolbar, or sources table). */
    variant?: "full" | "thread";
  }

  let { result, hideToolbar = false, variant = "full" }: Props = $props();
  const thread = $derived(variant === "thread");
  const showToolbar = $derived(!hideToolbar && !thread);
  const showToc = $derived(!thread);
  const showSources = $derived(!thread);
  let saving = $state(false);
  let saveMessage = $state("");
  let saveError = $state(false);
  let vaultFiles = $state<VaultFileRef[]>([]);

  const sections = $derived(parseReportSections(result.report));
  const sourceRows = $derived(parseSourcesSection(result.report));
  /** Single continuous flow — include all sections once; sources rendered as table if parsed */
  const bodySections = $derived(
    sections.filter((s) => !/^sources?/i.test(s.title)),
  );
  const leadSections = $derived(
    bodySections.filter((s) => isLeadTitle(s.title)),
  );
  const restSections = $derived(
    bodySections.filter((s) => !isLeadTitle(s.title)),
  );
  /** Thread shows summary + findings first; longer sections sit behind a disclosure. */
  const threadLead = $derived(
    thread && leadSections.length ? leadSections : bodySections,
  );
  const threadRest = $derived(
    thread && leadSections.length ? restSections : [],
  );

  function isLeadTitle(title: string): boolean {
    return isLeadSectionTitle(title);
  }

  function isFindingsTitle(title: string): boolean {
    return isFindingsSectionTitle(title);
  }
  const sourceSentence = $derived(
    formatRetrievalSummary(result.retrieval_stats ?? {}),
  );

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void (async () => {
      try {
        const root = workspace.vaultRoot ?? (await getVaultRoot());
        vaultFiles = flattenVaultFiles(await loadVaultTree(root));
      } catch {
        vaultFiles = [];
      }
    })();
  });

  const citeTitles = $derived(new Map(sourceRows.map((r) => [r.index, r.label] as const)));

  function sourceForCite(el: Element | null) {
    if (!el) return null;
    const n = Number(el.getAttribute("data-cite"));
    if (!Number.isFinite(n)) return null;
    return sourceRows.find((r) => r.index === n) ?? null;
  }

  function onProseClick(e: MouseEvent) {
    const el = (e.target as HTMLElement | null)?.closest?.("sup.cite") ?? null;
    const row = sourceForCite(el);
    if (!row) return;
    e.preventDefault();
    openSourceLabel(row.label);
  }

  function onProseKey(e: KeyboardEvent) {
    if (e.key !== "Enter" && e.key !== " ") return;
    const el = e.target as HTMLElement | null;
    const row = sourceForCite(el?.closest?.("sup.cite") ?? null);
    if (!row) return;
    e.preventDefault();
    openSourceLabel(row.label);
  }

  async function ensureVaultFiles(): Promise<VaultFileRef[]> {
    if (vaultFiles.length) return vaultFiles;
    try {
      const root = workspace.vaultRoot ?? (await getVaultRoot());
      vaultFiles = flattenVaultFiles(await loadVaultTree(root));
    } catch {
      vaultFiles = [];
    }
    return vaultFiles;
  }

  async function openSourceLabel(label: string) {
    const origin = classifySourceOrigin(label);
    if (origin === "web" || origin === "arxiv" || origin === "notion") {
      const url = label.match(/https?:\/\/\S+/)?.[0];
      if (url && typeof window !== "undefined") window.open(url, "_blank", "noopener");
      return;
    }
    const files = await ensureVaultFiles();
    const path = resolveSourcePath(label, workspace.vaultRoot, files);
    if (!path) return;
    const name = path.split(/[\\/]/).pop() ?? "Source";
    tabs.openNoteTab(path, name);
    workspace.setActiveNote(path);
  }

  function canOpenSource(label: string): boolean {
    const origin = classifySourceOrigin(label);
    if (origin === "web" || origin === "arxiv" || origin === "notion") return /https?:\/\//.test(label);
    return !!resolveSourcePath(label, workspace.vaultRoot, vaultFiles);
  }

  async function saveAsNote() {
    saving = true;
    saveMessage = "";
    saveError = false;
    try {
      const path = await saveResearchAsNote(result, {
        projectPath: workspace.activeTopicPath,
      });
      workspace.requestVaultRefresh();
      const label = path.split("/").pop() ?? "Research note";
      tabs.openNoteTab(path, label);
      workspace.setActiveNote(path);
      saveMessage = "Saved";
    } catch (e) {
      saveMessage = e instanceof Error ? e.message : "Save failed";
      saveError = true;
    } finally {
      saving = false;
    }
  }

  function exportMarkdown() {
    const blob = new Blob([result.report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const slug = result.query
      .slice(0, 40)
      .replace(/[^a-z0-9]+/gi, "-")
      .replace(/^-|-$/g, "")
      .toLowerCase();
    anchor.href = url;
    anchor.download = `research-${slug || "report"}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function scrollTo(id: string) {
    document.getElementById(`report-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
</script>

<article class="doc" class:thread data-testid="research-report">
  {#if showToolbar}
    <div class="toolbar">
      <button type="button" class="tbtn" onclick={saveAsNote} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </button>
      <button type="button" class="tbtn" onclick={exportMarkdown}>Export</button>
      <span class="meta conf">{sourceSentence}</span>
      {#if saveMessage}
        <span class="save-msg" class:error={saveError}>{saveMessage}</span>
      {/if}
    </div>
  {/if}

  {#if showToc && bodySections.length > 1}
    <nav class="toc" aria-label="Sections">
      {#each bodySections as s}
        <button type="button" class="toc-link" onclick={() => scrollTo(s.id)}>{displayReportTitle(s.title)}</button>
      {/each}
      {#if sourceRows.length}
        <button type="button" class="toc-link" onclick={() => scrollTo("sources")}>Sources</button>
      {/if}
    </nav>
  {/if}

  <div
    class="prose"
    onclick={onProseClick}
    onkeydown={onProseKey}
    role="presentation"
  >
    {#snippet sectionBlock(s: ReportSection)}
      <section
        class="sec"
        class:findings={isFindingsTitle(s.title)}
        class:summary={!isFindingsTitle(s.title) && isLeadTitle(s.title)}
        id="report-{s.id}"
      >
        <h2>{displayReportTitle(s.title)}</h2>
        <div class="sec-body">
          {@html renderSectionBody(s.body, citeTitles)}
        </div>
      </section>
    {/snippet}

    {#if thread}
      {#each threadLead as s (s.id)}
        {@render sectionBlock(s)}
      {/each}
      {#if threadRest.length}
        <details class="more">
          <summary>Read the details</summary>
          <div class="more-body">
            {#each threadRest as s (s.id)}
              {@render sectionBlock(s)}
            {/each}
          </div>
        </details>
      {/if}
    {:else}
      {#each bodySections as s (s.id)}
        {@render sectionBlock(s)}
      {/each}
    {/if}

    {#if showSources && sourceRows.length}
      <section class="sec" id="report-sources">
        <h2>Sources</h2>
        <div class="src-list">
          {#each sourceRows as row}
            <div class="src-row">
              <span class="idx">[{row.index}]</span>
              {#if row.origin}
                <span class="origin">{row.origin}</span>
              {/if}
              {#if canOpenSource(row.label)}
                <button
                  type="button"
                  class="ref link"
                  title="Open source"
                  onclick={() => openSourceLabel(row.label)}
                >
                  {row.label}
                </button>
              {:else}
                <span class="ref">{row.label}</span>
              {/if}
            </div>
          {/each}
        </div>
      </section>
    {/if}

    {#if !bodySections.length}
      <div class="sec-body">
        {@html renderSectionBody(result.report, citeTitles)}
      </div>
    {/if}
  </div>
</article>

<style>
  .doc {
    min-width: 0;
    max-width: 40rem;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 0.15rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }

  .tbtn {
    background: transparent;
    color: var(--text-faint);
    font-size: var(--text-xs);
    font-weight: var(--font-normal);
    min-height: 28px;
    padding: 0.25rem 0.5rem;
    border-radius: var(--radius-sm);
  }

  .tbtn:hover:not(:disabled) {
    color: var(--text);
    background: var(--surface-hover);
  }

  .meta {
    margin-left: 0.35rem;
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.35;
    max-width: 28rem;
  }

  .save-msg {
    font-size: var(--text-xs);
    color: var(--success);
    margin-left: 0.35rem;
  }

  .save-msg.error {
    color: var(--error);
  }

  .toc {
    display: flex;
    flex-wrap: wrap;
    gap: 0.15rem 0.75rem;
    margin-bottom: 1.5rem;
    padding-bottom: 0.85rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .toc-link {
    background: transparent;
    color: var(--text-faint);
    font-size: var(--text-xs);
    font-weight: var(--font-normal);
    min-height: auto;
    padding: 0.15rem 0;
    border-radius: 0;
  }

  .toc-link:hover {
    color: var(--text-muted);
  }

  .prose {
    font-size: var(--text-sm);
    line-height: 1.65;
  }

  .sec {
    margin-bottom: 1.75rem;
  }

  .sec h2 {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text);
    margin-bottom: 0.65rem;
    letter-spacing: -0.015em;
  }

  .sec-body :global(p) {
    color: var(--text-muted);
    margin-bottom: 0.65rem;
  }

  .sec-body :global(ul) {
    padding-left: 1.15rem;
    margin-bottom: 0.65rem;
  }

  .sec-body :global(li) {
    color: var(--text-muted);
    margin-bottom: 0.35rem;
  }

  .sec-body :global(sup.cite) {
    color: var(--text-faint);
    font-family: var(--font-mono);
    font-size: 0.7em;
    cursor: pointer;
  }

  .sec-body :global(sup.cite:hover) {
    color: var(--text);
    text-decoration: underline;
  }

  .src-list {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .src-row {
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 0.5rem;
    align-items: baseline;
    font-size: var(--text-xs);
    line-height: 1.45;
  }

  .idx {
    font-family: var(--font-mono);
    color: var(--text-faint);
  }

  .origin {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
  }

  .ref {
    color: var(--text-muted);
    word-break: break-word;
  }

  .ref.link {
    background: transparent;
    text-align: left;
    font-size: inherit;
    font-weight: var(--font-normal);
    min-height: auto;
    padding: 0;
    color: var(--accent-link);
    border-radius: 0;
  }

  .ref.link:hover {
    color: var(--text);
    text-decoration: underline;
  }

  .doc.thread {
    max-width: none;
  }

  .doc.thread .prose {
    font-size: var(--text-base);
    line-height: 1.72;
    color: var(--text);
  }

  .doc.thread .sec {
    margin-bottom: 1.85rem;
  }

  .doc.thread .sec:last-child {
    margin-bottom: 0.35rem;
  }

  .doc.thread .sec h2 {
    font-size: var(--text-xl);
    font-weight: 650;
    letter-spacing: -0.028em;
    line-height: 1.3;
    margin: 0 0 0.7rem;
    color: var(--text);
  }

  .doc.thread .sec-body :global(p) {
    color: var(--text);
    margin: 0 0 0.85rem;
    max-width: 42em;
  }

  .doc.thread .sec-body :global(p:last-child) {
    margin-bottom: 0;
  }

  .doc.thread .sec-body :global(ul),
  .doc.thread .sec-body :global(ol) {
    padding-left: 1.35rem;
    margin: 0.15rem 0 0.35rem;
  }

  .doc.thread .sec-body :global(li) {
    color: var(--text);
    margin-bottom: 0.55rem;
    line-height: 1.65;
  }

  .doc.thread .sec.findings .sec-body :global(li) {
    margin-bottom: 0.75rem;
    padding-left: 0.15rem;
  }

  .doc.thread .sec-body :global(strong) {
    font-weight: 620;
  }

  .doc.thread .sec-body :global(sup.cite) {
    color: var(--text-faint);
    font-family: var(--font-sans);
    font-size: 0.68em;
    font-weight: var(--font-medium);
    letter-spacing: 0.01em;
    margin-left: 0.08em;
    top: -0.35em;
    cursor: pointer;
  }

  .doc.thread .sec-body :global(sup.cite:hover) {
    color: var(--text);
    text-decoration: underline;
  }

  .doc.thread .sec-body :global(code) {
    font-family: var(--font-mono);
    font-size: 0.86em;
    background: var(--control-fill);
    border-radius: var(--radius-sm);
    padding: 0.1em 0.35em;
  }

  .doc.thread .more {
    margin: 0.35rem 0 0.15rem;
  }

  .doc.thread .more summary {
    cursor: pointer;
    list-style: none;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
    user-select: none;
    padding: 0.15rem 0;
  }

  .doc.thread .more summary::-webkit-details-marker {
    display: none;
  }

  .doc.thread .more summary::before {
    content: "";
    width: 0;
    height: 0;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
    border-left: 5px solid color-mix(in srgb, var(--text) 38%, transparent);
    flex-shrink: 0;
  }

  .doc.thread .more[open] summary::before {
    transform: rotate(90deg);
  }

  .doc.thread .more-body {
    margin-top: 1.1rem;
  }
</style>
