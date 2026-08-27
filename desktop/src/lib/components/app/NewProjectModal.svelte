<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { app } from "$lib/stores/app.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { tabs } from "$lib/stores/tabs.svelte";
  import { createProjectFolder, listProjectSubfolders, readProjectIdea, updateProjectFolder, type ProjectFolderSpec } from "$lib/vault/load";
  import { folderNameFromPath } from "$lib/vault/project-edit";
  import { FolderPlus, FolderOpen, Folder, X, Plus, Trash2 } from "@lucide/svelte";

  const IDEA_CHIPS = [
    { label: "Digital garden", idea: "A personal knowledge garden for notes, links, and growing ideas." },
    { label: "Budget tracker", idea: "Track spending, budgets, and financial goals over time." },
    { label: "Workout plan", idea: "Training logs, programs, and recovery notes." },
    { label: "Research log", idea: "Literature notes, open questions, and synthesis for a research topic." },
    { label: "Music toy", idea: "Experiments, samples, and production ideas for music projects." },
    { label: "Habit tracker", idea: "Daily habits, streaks, and reflection prompts." },
  ];

  type FolderRow = ProjectFolderSpec | { kind: "existing"; name: string };

  let name = $state("");
  let idea = $state("");
  let folders = $state<FolderRow[]>([]);
  let folderDraft = $state("");
  let addingFolder = $state(false);
  let busy = $state(false);
  let error = $state("");
  let nameEl: HTMLInputElement | undefined = $state();
  let hydratedFor = $state<string | null>(null);

  const isEdit = $derived(!!app.editingProjectPath);
  const canSubmit = $derived(name.trim().length > 0 && !busy);

  function reset() {
    name = "";
    idea = "";
    folders = [];
    folderDraft = "";
    addingFolder = false;
    busy = false;
    error = "";
    // Leave hydratedFor alone — the open $effect owns it. Clearing it here
    // re-triggers that effect and loops reset/focus forever (modal looks dead).
  }

  function close() {
    app.closeNewProject();
    reset();
  }

  function onBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) close();
  }

  function applyChip(chip: (typeof IDEA_CHIPS)[number]) {
    if (!name.trim()) name = chip.label;
    idea = chip.idea;
  }

  function startAddFolder() {
    addingFolder = true;
    folderDraft = "";
  }

  function basename(p: string): string {
    const parts = p.split(/[\\/]/).filter(Boolean);
    return parts[parts.length - 1] ?? p;
  }

  function shortPath(p: string, max = 42): string {
    if (p.length <= max) return p;
    return `…${p.slice(-(max - 1))}`;
  }

  function commitFolder() {
    const f = folderDraft.replace(/[\\/]/g, "-").trim();
    if (f && !folders.some((x) => x.name.toLowerCase() === f.toLowerCase())) {
      folders = [...folders, { kind: "create", name: f }];
    }
    folderDraft = "";
    addingFolder = false;
  }

  async function chooseExistingFolders() {
    error = "";
    try {
      const selected = await open({
        directory: true,
        multiple: true,
        title: "Choose folders to add to this project",
      });
      if (!selected) return;
      const paths = Array.isArray(selected) ? selected : [selected];
      const next = [...folders];
      for (const sourcePath of paths) {
        if (typeof sourcePath !== "string" || !sourcePath.trim()) continue;
        let base = basename(sourcePath).replace(/[\\/]/g, "-").trim() || "folder";
        let candidate = base;
        let i = 2;
        while (next.some((x) => x.name.toLowerCase() === candidate.toLowerCase())) {
          candidate = `${base} (${i})`;
          i += 1;
        }
        next.push({ kind: "import", name: candidate, sourcePath });
      }
      folders = next;
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not open folder picker";
    }
  }

  function removeFolder(i: number) {
    if (folders[i]?.kind === "existing") return;
    folders = folders.filter((_, idx) => idx !== i);
  }

  async function hydrateEdit(path: string) {
    busy = true;
    error = "";
    try {
      name = folderNameFromPath(path);
      idea = await readProjectIdea(path);
      const existing = await listProjectSubfolders(path);
      folders = existing.map((n) => ({ kind: "existing" as const, name: n }));
      folderDraft = "";
      addingFolder = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Could not load workspace";
    } finally {
      busy = false;
      requestAnimationFrame(() => nameEl?.focus());
    }
  }

  async function submit() {
    if (!canSubmit) return;
    busy = true;
    error = "";
    try {
      const newFolders = folders.filter((f): f is ProjectFolderSpec => f.kind !== "existing");
      const importedNotes = newFolders.some((f) => f.kind === "import");
      const editPath = app.editingProjectPath;
      if (editPath) {
        const newPath = await updateProjectFolder(editPath, {
          name: name.trim(),
          idea,
          folders: newFolders.length ? newFolders : undefined,
        });
        if (newPath !== editPath) {
          assistant.rebindProjectPath(editPath, newPath);
          workspace.rebindTopicPath(editPath, newPath);
        }
        workspace.setActiveTopic(newPath);
        workspace.requestVaultRefresh();
        void workspace.syncProjectsFromDisk();
        close();
        // Only file claims when folders with notes were imported — empty edit must not
        // spawn a failed "Remember topic notes" chat.
        if (importedNotes) void assistant.rememberTopicNotes(newPath);
        return;
      }
      const path = await createProjectFolder(name.trim(), {
        idea: idea.trim() || undefined,
        folders: newFolders.length ? newFolders : undefined,
      });
      workspace.setActiveTopic(path);
      tabs.newSessionTab({ projectPath: path });
      workspace.requestVaultRefresh();
      void workspace.syncProjectsFromDisk();
      close();
      if (importedNotes) void assistant.rememberTopicNotes(path);
    } catch (e) {
      error = e instanceof Error ? e.message : isEdit ? "Could not save workspace" : "Could not create project";
    } finally {
      busy = false;
    }
  }

  $effect(() => {
    if (!app.newProjectOpen) {
      hydratedFor = null;
      return;
    }
    const editPath = app.editingProjectPath;
    if (editPath) {
      if (hydratedFor !== editPath) {
        hydratedFor = editPath;
        void hydrateEdit(editPath);
      }
      return;
    }
    if (hydratedFor !== "") {
      hydratedFor = "";
      reset();
      requestAnimationFrame(() => nameEl?.focus());
    }
  });
</script>

{#if app.newProjectOpen}
  <div
    class="overlay-backdrop"
    role="presentation"
    onclick={onBackdrop}
  >
    <div
      class="overlay-panel dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-project-title"
      onclick={(e) => e.stopPropagation()}
    >
      <header class="head">
        <div>
          <h2 id="new-project-title">{isEdit ? "Edit workspace" : "New workspace"}</h2>
          <p class="sub">
            {isEdit
              ? "Rename this workspace, update the idea, or add folders."
              : "Name a workspace and add folders. Imported notes are filed as claims."}
          </p>
        </div>
        <button type="button" class="icon-close" aria-label="Close" onclick={close}>
          <X size={18} strokeWidth={1.75} />
        </button>
      </header>

      <div class="body">
        <label class="field">
          <span class="sr-only">Project name</span>
          <input
            bind:this={nameEl}
            class="name-input"
            type="text"
            placeholder="e.g. Skunkworks"
            bind:value={name}
            disabled={busy}
            onkeydown={(e) => {
              if (e.key === "Enter" && canSubmit) {
                e.preventDefault();
                void submit();
              }
            }}
          />
        </label>

        <section class="section">
          <div class="section-label">Folders</div>
          {#if folders.length === 0 && !addingFolder}
            <p class="muted">No folders added yet.</p>
          {:else}
            <ul class="folder-list">
              {#each folders as f, i (f.kind === "import" ? f.sourcePath : `${f.kind}:${f.name}`)}
                <li>
                  {#if f.kind === "import"}
                    <FolderOpen size={14} strokeWidth={1.75} />
                  {:else if f.kind === "existing"}
                    <Folder size={14} strokeWidth={1.75} />
                  {:else}
                    <FolderPlus size={14} strokeWidth={1.75} />
                  {/if}
                  <div class="folder-meta">
                    <span class="folder-name">{f.name}</span>
                    {#if f.kind === "import"}
                      <span class="folder-hint" title={f.sourcePath}>{shortPath(f.sourcePath)}</span>
                    {:else if f.kind === "existing"}
                      <span class="folder-hint">Already in workspace</span>
                    {:else}
                      <span class="folder-hint">New empty folder</span>
                    {/if}
                  </div>
                  {#if f.kind !== "existing"}
                    <button
                      type="button"
                      class="icon-tiny"
                      aria-label="Remove {f.name}"
                      onclick={() => removeFolder(i)}
                      disabled={busy}
                    >
                      <Trash2 size={13} strokeWidth={1.75} />
                    </button>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
          {#if addingFolder}
            <div class="folder-add-row">
              <input
                class="folder-input"
                type="text"
                placeholder="Folder name"
                bind:value={folderDraft}
                disabled={busy}
                onkeydown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    commitFolder();
                  }
                  if (e.key === "Escape") {
                    addingFolder = false;
                    folderDraft = "";
                  }
                }}
              />
              <button type="button" class="btn-text" onclick={commitFolder}>Add</button>
            </div>
          {:else}
            <div class="folder-actions">
              <button type="button" class="add-folder" onclick={startAddFolder} disabled={busy}>
                <Plus size={15} strokeWidth={2} />
                Create folder
              </button>
              <button
                type="button"
                class="add-folder"
                onclick={() => void chooseExistingFolders()}
                disabled={busy}
              >
                <FolderOpen size={15} strokeWidth={1.75} />
                Choose existing…
              </button>
            </div>
          {/if}
        </section>

        <section class="section">
          <div class="section-label">Idea</div>
          <textarea
            class="idea"
            rows={4}
            placeholder="What's this project about? (saved to IDEA.md)"
            bind:value={idea}
            disabled={busy}
          ></textarea>
          {#if !isEdit}
            <div class="chips">
              {#each IDEA_CHIPS as chip (chip.label)}
                <button type="button" class="chip" onclick={() => applyChip(chip)}>
                  {chip.label}
                </button>
              {/each}
            </div>
          {/if}
        </section>

        {#if error}
          <p class="err">{error}</p>
        {/if}
      </div>

      <footer class="foot">
        <button type="button" class="btn ghost" onclick={close} disabled={busy}>Cancel</button>
        <button
          type="button"
          class="btn primary"
          disabled={!canSubmit}
          onclick={() => void submit()}
        >
          {busy ? (isEdit ? "Saving…" : "Creating…") : isEdit ? "Save" : "Create"}
        </button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .dialog {
    width: min(440px, 94vw);
    max-height: min(90vh, 640px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.15rem 1.2rem 0.65rem;
  }

  h2 {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    letter-spacing: -0.02em;
    color: var(--text);
  }

  .sub {
    margin: 0.3rem 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    line-height: 1.4;
  }

  .icon-close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    min-height: 32px;
    padding: 0;
    border: none;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    flex-shrink: 0;
  }

  .icon-close:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .body {
    padding: 0.35rem 1.2rem 0.5rem;
    overflow-y: auto;
    flex: 1;
    min-height: 0;
  }

  .field {
    display: block;
    margin-bottom: 1rem;
  }

  .name-input {
    width: 100%;
    height: 42px;
    padding: 0 0.85rem;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface);
    color: var(--text);
    font-size: var(--text-md);
  }

  .name-input::placeholder {
    color: var(--text-muted);
    opacity: 1;
  }

  .name-input:focus {
    outline: none;
    border-color: var(--accent-live);
    box-shadow: 0 0 0 3px var(--focus-ring);
  }

  .section {
    margin-bottom: 1rem;
  }

  .section-label {
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    color: var(--text);
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .sel-count {
    font-size: var(--text-2xs);
    font-weight: var(--font-medium);
    color: var(--accent-live);
    background: var(--accent-live-dim);
    border-radius: var(--radius-full);
    padding: 0.1rem 0.5rem;
  }

  .chat-picker {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 0.45rem;
    background: var(--control-fill);
  }

  .chat-search {
    width: 100%;
    height: 32px;
    margin-bottom: 0.4rem;
    padding: 0 0.6rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--text);
    font-size: var(--text-sm);
  }

  .chat-search:focus {
    outline: none;
    border-color: var(--border-active);
  }

  .chat-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    max-height: 11rem;
    overflow-y: auto;
  }

  .chat-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    width: 100%;
    text-align: left;
    background: transparent;
    border: none;
    border-radius: var(--radius-md);
    padding: 0.4rem 0.45rem;
    cursor: pointer;
    color: inherit;
    font: inherit;
  }

  .chat-row:hover:not(:disabled) {
    background: var(--chrome-action-hover);
  }

  .chat-row:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .check {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    min-width: 16px;
    border-radius: var(--radius-xs);
    border: 1.5px solid var(--border);
    background: transparent;
    color: var(--accent-contrast);
    flex-shrink: 0;
    transition:
      background var(--dur-control) var(--ease-out),
      border-color var(--dur-control) var(--ease-out);
  }

  .check.on {
    background: var(--accent-live);
    border-color: var(--accent-live);
  }

  .chat-meta {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
  }

  .chat-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chat-sub {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .hint {
    margin: 0.4rem 0 0;
    font-size: var(--text-2xs);
    color: var(--text-faint);
  }

  .muted {
    margin: 0 0 0.4rem;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .folder-list {
    list-style: none;
    margin: 0 0 0.4rem;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .folder-list li {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.45rem;
    border-radius: var(--radius-md);
    background: var(--control-fill);
    color: var(--text);
    font-size: var(--text-sm);
  }

  .folder-meta {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
  }

  .folder-name {
    color: var(--text);
    font-weight: var(--font-medium);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .folder-hint {
    font-size: var(--text-2xs);
    color: var(--text-faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .icon-tiny {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    min-height: 26px;
    padding: 0;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
  }

  .icon-tiny:hover:not(:disabled) {
    color: var(--error);
    background: var(--error-dim);
  }

  .folder-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem 0.85rem;
    align-items: center;
  }

  .add-folder {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    min-height: 30px;
    padding: 0.2rem 0.15rem;
    cursor: pointer;
  }

  .add-folder:hover:not(:disabled) {
    color: var(--accent-live);
  }

  .add-folder:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .folder-add-row {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    margin-top: 0.25rem;
  }

  .folder-input {
    flex: 1;
    height: 34px;
    padding: 0 0.65rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    font-size: var(--text-sm);
  }

  .btn-text {
    background: transparent;
    border: none;
    color: var(--text);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    min-height: 34px;
    cursor: pointer;
  }

  .btn-text:hover:not(:disabled) {
    color: var(--text);
    text-decoration: underline;
    text-underline-offset: 0.15em;
  }

  .idea {
    width: 100%;
    min-height: 5.5rem;
    padding: 0.7rem 0.85rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface);
    color: var(--text);
    font-size: var(--text-sm);
    line-height: 1.5;
    resize: vertical;
  }

  .idea::placeholder {
    color: var(--text-muted);
    opacity: 1;
  }

  .idea:focus {
    outline: none;
    border-color: var(--border-active);
    box-shadow: 0 0 0 3px var(--focus-ring);
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.55rem;
  }

  .chip {
    background: var(--control-fill);
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    color: var(--text);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    min-height: 28px;
    padding: 0.3rem 0.7rem;
    cursor: pointer;
  }

  .chip:hover {
    background: var(--selection-hover);
    color: var(--text);
    border-color: var(--border-active);
  }

  .err {
    margin: 0 0 0.5rem;
    font-size: var(--text-sm);
    color: var(--error);
  }

  .foot {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    padding: 0.75rem 1.2rem 1.1rem;
    border-top: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .btn {
    min-height: 36px;
    padding: 0.4rem 1rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: var(--font-semibold);
    border: none;
    cursor: pointer;
  }

  .btn.ghost {
    background: transparent;
    color: var(--text-muted);
  }

  .btn.ghost:hover:not(:disabled) {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .btn.primary {
    background: var(--accent);
    color: var(--accent-contrast);
  }

  .btn.primary:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .btn.primary:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }
</style>
