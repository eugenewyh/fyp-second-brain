<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { updateProjectFolder, type ProjectFolderSpec } from "$lib/vault/load";
  import { folderLabel } from "$lib/assistant/workspace-chats";
  import { FolderOpen, X } from "@lucide/svelte";

  type PendingImport = { sourcePath: string; name: string };

  let pending = $state<PendingImport[]>([]);
  let busy = $state(false);
  let message = $state("");
  let error = $state(false);

  const topicPath = $derived(workspace.activeTopicPath);
  const topicName = $derived(topicPath ? folderLabel(topicPath) : null);
  const canImport = $derived(!!topicPath && pending.length > 0 && !busy);

  function basename(p: string): string {
    const parts = p.split(/[\\/]/).filter(Boolean);
    return parts[parts.length - 1] ?? p;
  }

  function shortPath(p: string, max = 48): string {
    if (p.length <= max) return p;
    return `…${p.slice(-(max - 1))}`;
  }

  function uniqueName(base: string, used: Set<string>): string {
    let candidate = base.replace(/[\\/]/g, "-").trim() || "folder";
    let i = 2;
    while (used.has(candidate.toLowerCase())) {
      candidate = `${base} (${i})`;
      i += 1;
    }
    used.add(candidate.toLowerCase());
    return candidate;
  }

  async function pickFolders() {
    error = false;
    message = "";
    try {
      const selected = await open({
        directory: true,
        multiple: true,
        title: "Choose folders with notes to import",
      });
      if (!selected) return;
      const paths = Array.isArray(selected) ? selected : [selected];
      const used = new Set(pending.map((p) => p.name.toLowerCase()));
      const next = [...pending];
      for (const sourcePath of paths) {
        if (typeof sourcePath !== "string" || !sourcePath.trim()) continue;
        if (next.some((p) => p.sourcePath === sourcePath)) continue;
        const name = uniqueName(basename(sourcePath), used);
        next.push({ sourcePath, name });
      }
      pending = next;
    } catch (e) {
      message = e instanceof Error ? e.message : "Could not open folder picker";
      error = true;
    }
  }

  function removePending(i: number) {
    pending = pending.filter((_, idx) => idx !== i);
  }

  async function runImport() {
    if (!topicPath || !pending.length) return;
    busy = true;
    message = "";
    error = false;
    try {
      const folders: ProjectFolderSpec[] = pending.map((p) => ({
        kind: "import",
        name: p.name,
        sourcePath: p.sourcePath,
      }));
      await updateProjectFolder(topicPath, { folders });
      pending = [];
      workspace.requestVaultRefresh();
      void workspace.syncProjectsFromDisk();
      await workspace.refreshChannelEmpty();
      await assistant.rememberTopicNotes(topicPath);
      message = "Imported and filing into memory — watch the chat for progress.";
      app.closeSheet();
      app.openHome();
    } catch (e) {
      message = e instanceof Error ? e.message : "Couldn't import notes";
      error = true;
    } finally {
      busy = false;
    }
  }
</script>

<div class="library" data-testid="library-panel">
  <header class="hero">
    <h2 class="title">Import notes into memory</h2>
    <p class="sub">
      {#if topicName}
        Folders are copied into <strong>{topicName}</strong>, then filed as claims —
        the same path as creating a workspace with imports.
      {:else}
        Choose or create a workspace first, then import folders of notes.
      {/if}
    </p>
  </header>

  {#if !topicPath}
    <div class="empty-workspace">
      <p>No active workspace.</p>
      <button type="button" class="text-link" onclick={() => app.openNewProject()}>
        Create workspace
      </button>
    </div>
  {:else}
    <section class="import-card" aria-label="Import folders">
      <button type="button" class="drop" onclick={() => void pickFolders()} disabled={busy}>
        <FolderOpen size={22} strokeWidth={1.75} />
        <span class="drop-title">Choose folders</span>
        <span class="drop-desc">Markdown, text, and PDFs inside will be filed as claims</span>
      </button>

      {#if pending.length}
        <ul class="pending">
          {#each pending as item, i (item.sourcePath)}
            <li>
              <div class="pending-meta">
                <span class="pending-name">{item.name}</span>
                <span class="pending-path" title={item.sourcePath}>{shortPath(item.sourcePath)}</span>
              </div>
              <button
                type="button"
                class="icon-btn"
                aria-label="Remove {item.name}"
                disabled={busy}
                onclick={() => removePending(i)}
              >
                <X size={14} strokeWidth={2} />
              </button>
            </li>
          {/each}
        </ul>
      {/if}

      <div class="actions">
        <button
          type="button"
          class="primary"
          disabled={!canImport}
          onclick={() => void runImport()}
        >
          {busy ? "Importing…" : pending.length > 1 ? `Import ${pending.length} folders` : "Import & file to memory"}
        </button>
        {#if pending.length}
          <button type="button" class="ghost" disabled={busy} onclick={() => void pickFolders()}>
            Add more
          </button>
        {/if}
      </div>
    </section>
  {/if}

  {#if message}
    <p class="message" class:error>{message}</p>
  {/if}
</div>

<style>
  .library {
    display: flex;
    flex-direction: column;
    gap: 1.15rem;
    padding: 1rem 1.15rem 1.25rem;
  }

  .hero {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
    color: var(--text);
    line-height: 1.25;
  }

  .sub {
    margin: 0;
    max-width: 34rem;
    font-size: var(--text-sm);
    line-height: 1.5;
    color: var(--text-muted);
  }

  .sub strong {
    color: var(--text);
    font-weight: var(--font-medium);
  }

  .empty-workspace {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.35rem 0.65rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .text-link {
    padding: 0;
    border: none;
    background: none;
    color: var(--text);
    font: inherit;
    font-weight: var(--font-medium);
    text-decoration: underline;
    text-underline-offset: 0.18em;
    text-decoration-color: color-mix(in srgb, var(--text) 35%, transparent);
    cursor: pointer;
    min-height: auto;
  }

  .text-link:hover {
    text-decoration-color: var(--text);
  }

  .import-card {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .drop {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    width: 100%;
    padding: 1rem 1.05rem;
    border: 1px dashed var(--border);
    border-radius: var(--radius-lg);
    background: transparent;
    text-align: left;
    cursor: pointer;
    color: var(--text);
    min-height: auto;
  }

  .drop:hover:not(:disabled) {
    border-color: var(--text-faint);
    background: var(--control-fill);
  }

  .drop:disabled {
    opacity: 0.55;
    cursor: wait;
  }

  .drop :global(svg) {
    color: var(--text-muted);
    margin-bottom: 0.2rem;
  }

  .drop-title {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
  }

  .drop-desc {
    font-size: var(--text-xs);
    color: var(--text-muted);
    line-height: 1.4;
  }

  .pending {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .pending li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 0.55rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    background: var(--control-fill);
  }

  .pending-meta {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
  }

  .pending-name {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
  }

  .pending-path {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    padding: 0;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    flex-shrink: 0;
    min-height: auto;
  }

  .icon-btn:hover:not(:disabled) {
    color: var(--text);
    background: var(--selection-hover);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .primary {
    padding: 0.5rem 0.9rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--text);
    color: var(--bg);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .primary:hover:not(:disabled) {
    opacity: 0.92;
  }

  .primary:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .ghost {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    cursor: pointer;
    min-height: auto;
  }

  .ghost:hover:not(:disabled) {
    color: var(--text);
    border-color: var(--border);
  }

  .message {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .message.error {
    color: var(--error);
  }
</style>
