<script lang="ts">
  import { onMount, type Snippet } from "svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { api } from "$lib/api";
  import {
    modelDisplayName,
    modelPickerGroups,
    isFreeModel,
    shortModelLabel,
  } from "$lib/llm/models";
  import {
    Plus,
    ArrowUp,
    ChevronDown,
    Paperclip,
    Files,
    Search,
    Check,
    SlidersHorizontal,
    FileText,
    X,
  } from "@lucide/svelte";
  import { open } from "@tauri-apps/plugin-dialog";
  import {
    filterAttachablePaths,
    registerComposerDropTarget,
  } from "$lib/assistant/composer-dnd";
  import {
    skillPlaceholder,
    type ForcedJob,
  } from "$lib/assistant/composer-skills";

  type ModeAction = "ask" | "research" | "teach";

  const MODE_ITEMS: Array<{
    action: ModeAction;
    label: string;
    desc: string;
    job: "answer" | "research" | "file";
    tone: "ask" | "research" | "teach";
  }> = [
    {
      action: "teach",
      label: "Teach",
      desc: "Save notes or files into long-term memory",
      job: "file",
      tone: "teach",
    },
    {
      action: "ask",
      label: "Ask",
      desc: "Answer from what you've already taught Nous",
      job: "answer",
      tone: "ask",
    },
    {
      action: "research",
      label: "Research",
      desc: "Run a multi-agent mission with sources and a report",
      job: "research",
      tone: "research",
    },
  ];

  interface Props {
    offline: boolean;
    noteTitle: string | null;
    /** dock = bottom bar; center = mid-pane empty landing */
    variant?: "dock" | "center";
    placeholder?: string;
    /** Optional row above the center textarea (e.g. workspace picker). */
    header?: Snippet;
    onSubmit: () => void;
  }

  let {
    offline,
    noteTitle,
    variant = "dock",
    placeholder: placeholderOverride,
    header,
    onSubmit,
  }: Props = $props();

  let llmProvider = $state("nvidia");
  let llmModel = $state("");
  let modelOpen = $state(false);
  let modelQuery = $state("");
  let plusOpen = $state(false);
  let savingModel = $state(false);
  let inputEl: HTMLInputElement | HTMLTextAreaElement | undefined = $state();
  let plusWrapEl: HTMLDivElement | undefined = $state();
  let pillEl: HTMLDivElement | undefined = $state();
  let dockWrapEl: HTMLDivElement | undefined = $state();
  let modelSearchEl: HTMLInputElement | undefined = $state();
  let dragOver = $state(false);
  let htmlDragDepth = 0;

  const modelGroups = $derived(
    modelPickerGroups(llmProvider, llmModel, { query: modelQuery }),
  );

  const canSubmit = $derived(
    !offline &&
      !assistant.isLoading &&
      !connection.memorySearchBlocked &&
      (!!assistant.input.trim() || assistant.attachments.length > 0),
  );

  const activeMode = $derived(
    MODE_ITEMS.find((m) => m.job === assistant.forcedJob) ?? null,
  );

  const bottomModes = $derived(
    MODE_ITEMS.filter((m) => m.job !== assistant.forcedJob),
  );

  async function loadModel() {
    if (!connection.connected) return;
    try {
      const s = await api.getSettings();
      llmProvider = s.llm_provider || s.values.LLM_PROVIDER || "nvidia";
      llmModel = s.values.LLM_MODEL || "";
    } catch {
      /* ignore */
    }
  }

  async function selectModel(provider: string, model: string) {
    llmProvider = provider;
    llmModel = model;
    modelOpen = false;
    modelQuery = "";
    if (!connection.connected) return;
    savingModel = true;
    try {
      await api.updateSettings({
        LLM_PROVIDER: provider,
        LLM_MODEL: model,
      });
    } catch {
      /* keep local */
    } finally {
      savingModel = false;
    }
  }

  function toggleModelMenu() {
    modelOpen = !modelOpen;
    plusOpen = false;
    if (modelOpen) {
      modelQuery = "";
      requestAnimationFrame(() => modelSearchEl?.focus());
    }
  }

  const placeholder = $derived(
    placeholderOverride ??
      skillPlaceholder(assistant.forcedJob as ForcedJob),
  );

  function closeMenus() {
    modelOpen = false;
    plusOpen = false;
    modelQuery = "";
  }

  function togglePlus() {
    plusOpen = !plusOpen;
    modelOpen = false;
  }

  function runPlusAction(
    action: "ingest" | "attach" | "ask" | "research" | "teach",
  ) {
    plusOpen = false;
    if (action === "ask") {
      assistant.setForcedJob("answer");
      assistant.composerFocusNonce += 1;
      return;
    }
    if (action === "research") {
      assistant.setForcedJob("research");
      assistant.composerFocusNonce += 1;
      return;
    }
    if (action === "teach") {
      assistant.setForcedJob("file");
      assistant.composerFocusNonce += 1;
      return;
    }
    if (action === "ingest") {
      app.openSheet("ingest");
      return;
    }
    void pickAttachFiles();
  }

  function selectSkill(job: Exclude<ForcedJob, null>) {
    assistant.setForcedJob(job);
    plusOpen = false;
    modelOpen = false;
    assistant.composerFocusNonce += 1;
  }

  function clearForcedSkill() {
    assistant.setForcedJob(null);
    plusOpen = false;
    modelOpen = false;
    assistant.composerFocusNonce += 1;
  }

  const ATTACH_EXT = /\.(md|txt|pdf|docx)$/i;
  const DOCX_MIME =
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

  function isAttachableName(name: string, mime?: string): boolean {
    if (ATTACH_EXT.test(name)) return true;
    return (mime || "").split(";")[0].trim().toLowerCase() === DOCX_MIME;
  }

  async function pickAttachFiles() {
    try {
      const selected = await open({
        multiple: true,
        filters: [{ name: "Documents", extensions: ["md", "txt", "pdf", "docx"] }],
      });
      const paths = Array.isArray(selected) ? selected : selected ? [selected] : [];
      for (const path of paths) {
        const name = path.split(/[\\/]/).pop() ?? path;
        assistant.addAttachment({ name, path });
      }
    } catch {
      /* cancelled */
    }
  }

  function stagePaths(paths: string[]) {
    for (const path of filterAttachablePaths(paths)) {
      const name = path.split(/[\\/]/).pop() ?? path;
      assistant.addAttachment({ name, path });
    }
    if (filterAttachablePaths(paths).length) {
      assistant.composerFocusNonce += 1;
    }
  }

  async function stageDroppedFiles(fileList: FileList | File[]) {
    const files = Array.from(fileList);
    for (const f of files) {
      if (!isAttachableName(f.name, f.type)) continue;
      const path = (f as File & { path?: string }).path;
      let text: string | undefined;
      if (/\.(md|txt)$/i.test(f.name)) {
        try {
          text = (await f.text()).slice(0, 20000);
        } catch {
          /* ignore */
        }
      }
      assistant.addAttachment({ name: f.name, path, text });
    }
  }

  function pointInDropZone(clientX: number, clientY: number): boolean {
    const el = dockWrapEl ?? pillEl;
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return clientX >= r.left && clientX <= r.right && clientY >= r.top && clientY <= r.bottom;
  }

  function onDragEnter(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    htmlDragDepth += 1;
    dragOver = true;
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    dragOver = true;
  }

  function onDragLeave(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    htmlDragDepth = Math.max(0, htmlDragDepth - 1);
    if (htmlDragDepth === 0) dragOver = false;
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    htmlDragDepth = 0;
    dragOver = false;
    if (e.dataTransfer?.files?.length) void stageDroppedFiles(e.dataTransfer.files);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Tab" && e.shiftKey) {
      e.preventDefault();
      assistant.cycleForcedJob();
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      // Ignore key-repeat while the first submit is still routing.
      if (e.repeat || !canSubmit) return;
      onSubmit();
    }
    if (e.key === "Escape") closeMenus();
  }

  /** Grow/shrink the textarea with the draft (expands upward in the dock). */
  function autosizeInput() {
    const el = inputEl;
    if (!(el instanceof HTMLTextAreaElement)) return;
    el.style.height = "auto";
    const max = variant === "center" ? 12 * 16 : 8 * 16;
    el.style.height = `${Math.min(el.scrollHeight, max)}px`;
  }

  function onDocClick(e: MouseEvent) {
    if (!pillEl) return;
    if (pillEl.contains(e.target as Node)) return;
    if (plusOpen) plusOpen = false;
    if (modelOpen) {
      modelOpen = false;
      modelQuery = "";
    }
  }

  $effect(() => {
    if (connection.connected) void loadModel();
  });

  $effect(() => {
    const n = assistant.composerFocusNonce;
    if (n <= 0) return;
    requestAnimationFrame(() => {
      inputEl?.focus();
      inputEl?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    });
  });

  $effect(() => {
    void assistant.input;
    void variant;
    requestAnimationFrame(() => autosizeInput());
  });

  onMount(() => {
    void loadModel();
    document.addEventListener("click", onDocClick);

    const unregisterDrop = registerComposerDropTarget({
      setDragOver: (over) => {
        dragOver = over;
      },
      containsPoint: pointInDropZone,
      stagePaths,
    });

    return () => {
      document.removeEventListener("click", onDocClick);
      unregisterDrop();
    };
  });
</script>

{#snippet skillPills()}
  {#if bottomModes.length}
    <div class="skill-row" role="group" aria-label="Message skills" data-testid="composer-skills">
      {#each bottomModes as mode, i (mode.action)}
        <button
          type="button"
          class="skill-pill"
          class:tone-teach={mode.tone === "teach"}
          class:tone-ask={mode.tone === "ask"}
          class:tone-research={mode.tone === "research"}
          title={mode.desc}
          data-testid={`skill-${mode.tone}`}
          onclick={() => selectSkill(mode.job)}
        >
          <span>{mode.label}</span>
          {#if i === 0}
            <kbd class="skill-kbd">⇧Tab</kbd>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
{/snippet}

{#snippet activeSkillChip()}
  {#if activeMode}
    <button
      type="button"
      class="skill-pill skill-pill-active"
      class:tone-teach={activeMode.tone === "teach"}
      class:tone-ask={activeMode.tone === "ask"}
      class:tone-research={activeMode.tone === "research"}
      title={`${activeMode.desc} (click to clear)`}
      data-testid={`skill-active-${activeMode.tone}`}
      onclick={clearForcedSkill}
    >
      <span>{activeMode.label}</span>
    </button>
  {/if}
{/snippet}

{#snippet plusTrigger()}
  <div class="plus-wrap" bind:this={plusWrapEl}>
    <button
      type="button"
      class="icon-ghost"
      class:open={plusOpen}
      title="Add"
      aria-expanded={plusOpen}
      aria-haspopup="menu"
      onclick={(e) => {
        e.stopPropagation();
        togglePlus();
      }}
    >
      <Plus size={18} strokeWidth={2} />
    </button>
  </div>
{/snippet}

{#snippet plusPanel()}
  {#if plusOpen}
    <div
      class="plus-menu"
      class:plus-menu-below={variant === "center"}
      class:plus-menu-above={variant === "dock"}
      role="menu"
      aria-label="Add"
    >
      <div class="plus-section" role="group" aria-label="Files">
        <button
          type="button"
          class="plus-row"
          role="menuitem"
          onclick={() => runPlusAction("attach")}
        >
          <span class="row-icon" aria-hidden="true">
            <Paperclip size={15} strokeWidth={2} />
          </span>
          <span class="plus-label">Attach files…</span>
        </button>
        <button
          type="button"
          class="plus-row"
          role="menuitem"
          onclick={() => runPlusAction("ingest")}
        >
          <span class="row-icon" aria-hidden="true">
            <Files size={15} strokeWidth={2} />
          </span>
          <span class="plus-label">Documents &amp; files</span>
          <span class="plus-kbd">⌘U</span>
        </button>
      </div>
    </div>
  {/if}
{/snippet}

{#snippet modelPicker()}
  <div class="dd">
    <button
      type="button"
      class="dd-btn"
      data-testid="model-picker"
      disabled={offline || savingModel}
      aria-expanded={modelOpen}
      aria-haspopup="listbox"
      onclick={() => toggleModelMenu()}
      title="AI model"
    >
      <span class="dd-label">{shortModelLabel(llmModel) || "Model"}</span>
      <ChevronDown size={14} strokeWidth={2} />
    </button>
    {#if modelOpen}
      <div class="model-menu" role="listbox" aria-label="Models">
        <div class="model-search">
          <Search size={14} strokeWidth={2} aria-hidden="true" />
          <input
            bind:this={modelSearchEl}
            class="model-search-input"
            type="search"
            placeholder="Search models"
            bind:value={modelQuery}
            onclick={(e) => e.stopPropagation()}
            onkeydown={(e) => {
              if (e.key === "Escape") {
                e.stopPropagation();
                closeMenus();
              }
            }}
          />
        </div>
        <div class="model-list">
          {#if modelGroups.length === 0}
            <p class="model-empty">No models match</p>
          {:else}
            {#each modelGroups as group (group.providerId)}
              <p class="model-group-label">{group.label}</p>
              {#each group.models as m (group.providerId + ":" + m)}
                {@const selected = m === llmModel && group.providerId === llmProvider}
                <button
                  type="button"
                  class="model-row"
                  class:selected
                  role="option"
                  aria-selected={selected}
                  onclick={() => void selectModel(group.providerId, m)}
                >
                  <span class="model-row-name">{modelDisplayName(m)}</span>
                  {#if isFreeModel(m)}
                    <span class="model-free">Free</span>
                  {/if}
                  {#if selected}
                    <span class="model-check" aria-hidden="true">
                      <Check size={14} strokeWidth={2.5} />
                    </span>
                  {/if}
                </button>
              {/each}
            {/each}
          {/if}
        </div>
        <div class="model-foot">
          <button
            type="button"
            class="model-manage"
            onclick={() => {
              modelOpen = false;
              modelQuery = "";
              app.openSheet("settings");
            }}
          >
            <SlidersHorizontal size={14} strokeWidth={2} aria-hidden="true" />
            Manage models
          </button>
        </div>
      </div>
    {/if}
  </div>
{/snippet}

{#snippet sendButton()}
  <button
    type="button"
    class="send-soft"
    class:ready={canSubmit}
    class:busy={assistant.isLoading}
    data-testid="run-research"
    disabled={!canSubmit}
    onclick={onSubmit}
    title={offline
      ? "Backend offline"
      : connection.memorySearchBlocked
        ? "Memory unavailable"
        : assistant.isLoading
          ? "Working…"
          : "Send"}
    aria-label={assistant.isLoading ? "Working" : "Send"}
  >
    {#if assistant.isLoading}
      <span class="send-spinner" aria-hidden="true"></span>
    {:else}
      <ArrowUp size={18} strokeWidth={2.25} />
    {/if}
  </button>
{/snippet}

{#snippet attachChips()}
  {#if assistant.attachments.length}
    <div class="attach-row" aria-label="Attached files">
      {#each assistant.attachments as file (file.id)}
        <div class="attach-chip" title={file.path || file.name}>
          <FileText size={13} strokeWidth={2} aria-hidden="true" />
          <span class="attach-name">{file.name}</span>
          <button
            type="button"
            class="attach-remove"
            title="Remove {file.name}"
            aria-label="Remove {file.name}"
            onclick={() => assistant.removeAttachment(file.id)}
          >
            <X size={12} strokeWidth={2.25} />
          </button>
        </div>
      {/each}
    </div>
  {/if}
{/snippet}

<div
  class="dock-wrap"
  class:center={variant === "center"}
  class:dock={variant === "dock"}
  class:is-offline={offline}
  class:is-loading={assistant.isLoading}
  class:wrap-drag={dragOver}
  bind:this={dockWrapEl}
  role="region"
  aria-label="Message composer. Drop .md, .txt, .pdf, or .docx files to attach."
  ondragenter={onDragEnter}
  ondragover={onDragOver}
  ondragleave={onDragLeave}
  ondrop={onDrop}
>
  {#if noteTitle && variant === "dock"}
    <p class="context">Using {noteTitle}</p>
  {/if}

  {#if header && variant === "center"}
    <div class="composer-top">
      {@render header()}
    </div>
  {/if}

  <div
    class="pill"
    class:pill-center={variant === "center"}
    class:pill-dock={variant === "dock"}
    class:pill-offline={offline}
    class:pill-busy={assistant.isLoading}
    class:pill-drag={dragOver}
    bind:this={pillEl}
  >
    {#if variant === "center"}
      <!-- Tall multi-line composer + toolbar -->
      {@render attachChips()}
      <div class="pill-main">
        <textarea
          bind:this={inputEl}
          class="input input-center"
          data-testid="research-query"
          bind:value={assistant.input}
          placeholder={dragOver
            ? "Drop files to attach…"
            : offline
              ? "Backend offline — reconnect to send…"
              : placeholder}
          rows={3}
          onkeydown={handleKeydown}
          oninput={() => autosizeInput()}
          disabled={assistant.isLoading || offline}
          aria-disabled={assistant.isLoading || offline}
        ></textarea>
      </div>

      <div class="pill-bar">
        <div class="bar-left">
          {@render plusTrigger()}
          {@render activeSkillChip()}
          {@render modelPicker()}
        </div>
        <div class="bar-right">
          {@render sendButton()}
        </div>
      </div>
      {@render plusPanel()}
    {:else}
      <!-- Compact dock: input + toolbar -->
      {@render attachChips()}
      <div class="dock-input-row">
        <textarea
          bind:this={inputEl}
          class="input input-dock"
          data-testid="research-query"
          bind:value={assistant.input}
          placeholder={dragOver
            ? "Drop files to attach…"
            : offline
              ? "Backend offline — reconnect to send…"
              : placeholder}
          rows={1}
          onkeydown={handleKeydown}
          oninput={() => autosizeInput()}
          disabled={assistant.isLoading || offline}
          aria-disabled={assistant.isLoading || offline}
        ></textarea>
        {@render sendButton()}
      </div>

      <div class="pill-bar pill-bar-dock">
        <div class="bar-left">
          {@render plusTrigger()}
          {@render activeSkillChip()}
          {@render modelPicker()}
        </div>
      </div>
      {@render plusPanel()}
    {/if}
  </div>

  {@render skillPills()}

  {#if offline}
    <p class="privacy warn" role="status">Backend offline — reconnect to send</p>
  {:else if variant === "dock"}
    {#if connection.memorySearchBlocked}
      <p class="privacy warn" role="status">
        {#if connection.reindexBusy || connection.reindexRequired}
          Rebuilding search index…
        {:else if connection.reindexError}
          {connection.reindexError}
          <button type="button" class="linkish" onclick={() => void connection.retryReindex()}>
            Retry
          </button>
        {:else}
          {connection.embeddingsError || "Vault search unavailable"}
          <button type="button" class="linkish" onclick={() => void connection.retryReindex()}>
            Retry
          </button>
        {/if}
      </p>
    {:else if assistant.isLoading}
      <p class="privacy quiet live" role="status">
        <span class="status-dot" aria-hidden="true"></span>
        {assistant.routeStatus === "teach" ? "Filing into memory…" : "Working…"}
      </p>
    {/if}
  {:else if connection.memorySearchBlocked}
    <p class="privacy warn" role="status">
      {#if connection.reindexBusy || connection.reindexRequired}
        Rebuilding search index…
      {:else if connection.reindexError}
        {connection.reindexError}
        <button type="button" class="linkish" onclick={() => void connection.retryReindex()}>
          Retry
        </button>
      {:else}
        {connection.embeddingsError || "Vault search unavailable"}
        <button type="button" class="linkish" onclick={() => void connection.retryReindex()}>
          Retry
        </button>
      {/if}
    </p>
  {:else if assistant.isLoading}
    <p class="privacy quiet live" role="status">
      <span class="status-dot" aria-hidden="true"></span>
      {assistant.routeStatus === "teach" ? "Filing into memory…" : "Working…"}
    </p>
  {/if}
</div>

<style>
  .dock-wrap {
    flex-shrink: 0;
  }

  .dock-wrap.dock {
    position: relative;
    flex-shrink: 0;
    z-index: 2;
    padding: 0.65rem var(--chat-gutter, 1.5rem) 0.85rem;
    background: transparent;
    pointer-events: auto;
  }

  .dock-wrap.dock .pill {
    width: 100%;
    max-width: var(--chat-col, 45rem);
    margin: 0 auto;
  }

  .dock-wrap.center {
    position: relative;
    left: auto;
    right: auto;
    bottom: auto;
    z-index: 5;
    width: 100%;
    max-width: var(--chat-col, 45rem);
    margin: 0 auto;
    padding: 0;
    pointer-events: auto;
    background: none;
    overflow: visible;
  }

  .context {
    width: 100%;
    max-width: var(--chat-col, 45rem);
    margin: 0 auto 0.45rem;
    font-size: var(--text-sm);
    color: var(--text-faint);
    padding: 0;
  }

  .pill {
    width: 100%;
    max-width: var(--chat-col, 45rem);
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.65rem 0.7rem;
    /* Bordered field on paper (JTX form controls) — stays interactive */
    background: var(--control-fill);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    box-shadow: none;
    position: relative;
    z-index: 1;
  }

  /* —— Dock (active stage) —— */
  .pill.pill-dock {
    width: 100%;
    max-width: var(--chat-col, 45rem);
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding: 0;
    border-radius: var(--radius-xl);
    overflow: visible;
  }

  .dock-input-row {
    display: flex;
    align-items: flex-end;
    gap: 0.45rem;
    padding: 0.45rem 0.55rem 0.35rem 0.9rem;
    min-width: 0;
  }

  .input-dock {
    flex: 1;
    min-width: 0;
    width: auto;
    max-width: 100%;
    height: auto;
    min-height: 2.25rem;
    max-height: 8rem;
    padding: 0.45rem 0.15rem;
    border: none;
    background: transparent;
    resize: none;
    box-sizing: border-box;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
    overflow-x: hidden;
    overflow-y: auto;
    line-height: 1.45;
  }

  /* —— Center card —— */
  .pill.pill-center {
    max-width: none;
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding: 0;
    border-radius: var(--radius-xl);
    background: var(--bg-elevated, var(--control-fill));
    border: 1px solid var(--border);
    box-shadow: var(--shadow-composer);
    overflow: visible;
    min-height: 7.5rem;
  }

  .pill:focus-within {
    border-color: color-mix(in oklch, var(--accent-live) 35%, var(--border));
  }

  .pill.pill-center:focus-within {
    border-color: color-mix(in oklch, var(--accent-live) 40%, var(--border));
    box-shadow: var(--shadow-lg);
  }

  .pill.pill-offline {
    opacity: 0.78;
    border-color: color-mix(in srgb, var(--warning) 42%, var(--border));
    background: color-mix(in srgb, var(--warning) 5%, var(--control-fill));
  }

  .pill.pill-busy {
    border-color: var(--border-active);
    background: color-mix(in srgb, var(--accent-live) 4%, var(--control-fill));
  }

  .composer-top {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    margin: 0 0 0.25rem;
    /* Match pill content inset so the label sits past the rounded corner */
    padding: 0 1.1rem;
    min-width: 0;
  }

  .pill-main {
    width: 100%;
    min-width: 0;
    padding: 0.85rem 1.1rem 0.4rem;
  }

  textarea.input-center {
    display: block;
    flex: none;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    height: auto;
    min-height: 3.75rem;
    max-height: 12rem;
    padding: 0.15rem 0.1rem 0.4rem;
    font-size: var(--text-base);
    line-height: 1.5;
    color: var(--text);
    border: none !important;
    background: transparent;
    resize: none;
    box-sizing: border-box;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
    overflow-x: hidden;
    overflow-y: auto;
    outline: none;
  }

  .input-center:focus {
    outline: none !important;
    border: none !important;
  }

  .input-center::placeholder {
    color: var(--text-faint);
  }

  .pill-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.85rem;
    width: 100%;
    padding: 0.4rem 0.65rem 0.65rem 0.55rem;
    border-top: none;
    overflow: visible;
  }

  .pill-bar-dock {
    padding: 0.3rem 0.55rem 0.45rem;
  }

  .bar-left {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    min-width: 0;
    flex-wrap: wrap;
  }

  .bar-right {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-shrink: 0;
  }

  .attach-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    padding: 0.55rem 0.75rem 0;
  }

  .attach-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    max-width: 16rem;
    min-height: 26px;
    padding: 0.15rem 0.25rem 0.15rem 0.45rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-elevated);
    color: var(--text-muted);
    font-size: var(--type-body-sm-size);
    font-weight: var(--font-medium);
    line-height: 1.2;
  }

  .attach-chip :global(svg) {
    flex-shrink: 0;
    color: var(--text-faint);
  }

  .attach-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .attach-remove {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    min-width: 20px;
    min-height: 20px;
    padding: 0;
    border: none;
    border-radius: var(--radius-feedback);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
  }

  .attach-remove:hover,
  .attach-remove:focus-visible {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .pill-drag {
    border-color: var(--border-active) !important;
    background: color-mix(in srgb, var(--selection-bg) 55%, var(--bg-elevated)) !important;
    box-shadow: inset 0 0 0 1px var(--border-active);
  }

  .pill-drag .input::placeholder {
    color: var(--text-muted);
  }

  .plus-wrap {
    flex-shrink: 0;
  }

  .icon-ghost {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    min-height: 38px;
    padding: 0;
    border: none;
    border-radius: var(--radius-lg);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    flex-shrink: 0;
  }

  .icon-ghost:hover,
  .icon-ghost.open {
    color: var(--text);
    background: var(--surface-hover);
  }

  .icon-ghost :global(svg) {
    display: block;
  }

  /* + popup — full composer width, aligned to pill edges */
  .plus-menu {
    position: absolute;
    left: 0;
    right: 0;
    width: 100%;
    z-index: 80;
    padding: 0.45rem;
    background: var(--bg-elevated);
    border: 1px solid var(--stroke-nous);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-nous);
    animation: overlay-panel-in var(--dur-med) var(--ease-out) both;
  }

  .plus-menu-below {
    top: calc(100% + 8px);
    bottom: auto;
  }

  .plus-menu-above {
    bottom: calc(100% + 8px);
    top: auto;
  }

  .plus-section {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .skill-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
    gap: 0.4rem;
    width: 100%;
    max-width: var(--chat-col, 45rem);
    margin: 0.75rem auto 0;
    /* Match .composer-top inset so pills line up with workspace picker */
    padding: 0 1.1rem;
    min-width: 0;
    box-sizing: border-box;
  }

  .dock-wrap.dock .skill-row {
    margin-top: 0.55rem;
  }

  .skill-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    height: 32px;
    padding: 0 0.85rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    background: var(--bg-elevated, var(--bg));
    box-shadow: var(--shadow-sm);
    color: var(--text-muted);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    line-height: 1;
    letter-spacing: -0.01em;
    cursor: pointer;
    min-height: auto;
    transition:
      background 0.12s ease,
      border-color 0.12s ease,
      color 0.12s ease,
      box-shadow 0.12s ease;
  }

  .skill-pill:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
    border-color: var(--border-active, var(--border));
  }

  .skill-pill-active {
    background: var(--accent-live-dim);
    border-color: color-mix(in srgb, var(--accent-live) 45%, var(--border));
    color: var(--text);
  }

  .skill-pill-active.tone-teach {
    background: var(--warning-dim);
    border-color: color-mix(in srgb, var(--warning) 45%, var(--border));
  }

  .skill-pill-active.tone-ask {
    background: var(--success-dim);
    border-color: color-mix(in srgb, var(--success) 45%, var(--border));
  }

  .skill-pill-active.tone-research {
    background: var(--accent-live-dim);
    border-color: color-mix(in srgb, var(--accent-live) 45%, var(--border));
  }

  .skill-kbd {
    display: inline-flex;
    align-items: center;
    margin: 0;
    padding: 0.1rem 0.3rem;
    border: 1px solid color-mix(in srgb, currentColor 22%, transparent);
    border-radius: var(--radius-xs);
    background: color-mix(in srgb, currentColor 8%, transparent);
    color: var(--text-faint);
    font-family: inherit;
    font-size: var(--text-2xs);
    font-weight: var(--font-medium);
    line-height: 1.2;
    letter-spacing: 0;
  }

  .plus-row {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: var(--text-sm);
    padding: 0.45rem 0.6rem;
    border-radius: var(--radius-lg);
    cursor: pointer;
  }

  .plus-row:hover {
    background: var(--chrome-action-hover);
  }

  .row-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    flex-shrink: 0;
    color: var(--text-faint);
  }

  .row-icon :global(svg) {
    display: block;
  }

  .force-chip {
    display: inline-flex;
    align-items: center;
    height: 28px;
    padding: 0 0.55rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-full);
    background: var(--selection-bg);
    color: var(--text);
    font-size: var(--text-xs);
    font-weight: var(--font-medium);
    cursor: pointer;
  }

  .force-chip:hover {
    border-color: var(--border-active);
  }

  .plus-label {
    flex: 1;
    min-width: 0;
  }

  .plus-kbd {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: var(--text-sm);
    color: var(--text-faint);
    letter-spacing: 0.02em;
  }

  .plus-divider {
    height: 1px;
    margin: 0.3rem 0.45rem;
    background: var(--border-subtle);
  }

  .dd {
    position: relative;
    flex-shrink: 0;
  }

  .dd-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    min-height: 36px;
    padding: 0.4rem 0.65rem;
    border: none;
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--text-muted);
    font-size: var(--text-base);
    font-weight: var(--font-normal);
    cursor: pointer;
    max-width: 12rem;
  }

  .dd-btn:hover:not(:disabled) {
    color: var(--text);
    background: var(--surface-hover);
  }

  .dd-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .dd-btn :global(svg) {
    flex-shrink: 0;
    opacity: 0.65;
  }

  .dd-label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .model-menu {
    position: absolute;
    left: 0;
    bottom: calc(100% + 8px);
    z-index: 90;
    width: min(18.5rem, calc(100vw - 2rem));
    max-height: min(22rem, calc(100vh - 10rem));
    display: flex;
    flex-direction: column;
    background: var(--bg-elevated);
    border: 1px solid var(--stroke-nous);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-nous);
    overflow: hidden;
    animation: overlay-panel-in var(--dur-fast) var(--ease-out) both;
  }

  .model-search {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.65rem 0.75rem;
    border-bottom: 1px solid var(--border-subtle);
    color: var(--text-faint);
    flex-shrink: 0;
  }

  .model-search :global(svg) {
    flex-shrink: 0;
  }

  .model-search-input {
    flex: 1;
    min-width: 0;
    width: auto;
    height: auto;
    padding: 0;
    border: none !important;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: var(--text-sm);
    box-shadow: none;
  }

  .model-search-input:focus {
    outline: none !important;
    border: none !important;
  }

  .model-search-input::placeholder {
    color: var(--text-faint);
  }

  .model-list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 0.35rem 0.35rem 0.45rem;
  }

  .model-group-label {
    margin: 0.45rem 0.55rem 0.2rem;
    font-size: var(--text-2xs);
    font-weight: var(--font-medium);
    color: var(--text-faint);
    letter-spacing: 0.02em;
  }

  .model-row {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: var(--text-sm);
    padding: 0.45rem 0.55rem;
    border-radius: var(--radius-md);
    cursor: pointer;
  }

  .model-row:hover {
    background: var(--chrome-action-hover);
  }

  .model-row.selected {
    background: color-mix(in srgb, var(--accent-live) 12%, transparent);
    color: var(--text);
  }

  .model-row-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .model-free {
    flex-shrink: 0;
    font-size: var(--text-2xs);
    font-weight: var(--font-medium);
    line-height: 1;
    padding: 0.2rem 0.35rem;
    border-radius: var(--radius-xs);
    background: var(--border-subtle);
    color: var(--text-muted);
  }

  .model-check {
    flex-shrink: 0;
    display: inline-flex;
    color: var(--accent-live);
  }

  .model-empty {
    margin: 0.75rem 0.55rem;
    font-size: var(--text-sm);
    color: var(--text-faint);
  }

  .model-foot {
    flex-shrink: 0;
    border-top: 1px solid var(--border-subtle);
    padding: 0.3rem;
  }

  .model-manage {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    width: 100%;
    text-align: left;
    border: none;
    background: transparent;
    color: var(--text-muted);
    font: inherit;
    font-size: var(--text-sm);
    padding: 0.5rem 0.55rem;
    border-radius: var(--radius-md);
    cursor: pointer;
  }

  .model-manage:hover {
    background: var(--chrome-action-hover);
    color: var(--text);
  }

  .model-manage :global(svg) {
    flex-shrink: 0;
    opacity: 0.75;
  }

  .send-soft {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    min-height: 40px;
    padding: 0;
    border: none;
    border-radius: var(--radius-lg);
    background: var(--border-subtle);
    color: var(--text-faint);
    cursor: not-allowed;
    flex-shrink: 0;
    transition: background 0.12s ease, color 0.12s ease;
  }

  .send-soft.ready {
    background: var(--accent-live);
    color: var(--accent-on-live, #ffffff);
    cursor: pointer;
  }

  .send-soft.ready:hover {
    background: var(--accent-live-hover);
  }

  .send-soft.busy {
    background: var(--accent-live-dim);
    color: var(--accent-live);
    cursor: wait;
    opacity: 1;
  }

  .send-soft:disabled.busy {
    opacity: 1;
  }

  .send-soft :global(svg) {
    display: block;
  }

  .send-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid color-mix(in srgb, var(--accent-live) 28%, transparent);
    border-top-color: var(--accent-live);
    border-radius: 50%;
    animation: send-spin 0.7s linear infinite;
  }

  @keyframes send-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .input {
    /* Override global `input { width: 100% }` so flex siblings (send) stay visible */
    flex: 1 1 0;
    width: auto;
    min-width: 0;
    max-width: none;
    border: none !important;
    background: transparent;
    padding: 0.55rem 0.4rem;
    font-size: var(--text-md);
    color: var(--text);
    box-shadow: none;
  }

  input.input {
    height: 40px;
  }

  textarea.input {
    height: auto;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    word-break: break-word;
    overflow-x: hidden;
  }

  .input:focus {
    outline: none !important;
    border: none !important;
  }

  .input:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .pill-offline .input:disabled {
    opacity: 0.7;
  }

  .privacy {
    width: 100%;
    max-width: var(--chat-col, 45rem);
    margin: 0.4rem auto 0;
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    color: var(--warning);
    padding: 0 0.15rem;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.4rem;
  }

  .privacy.quiet {
    color: var(--text-faint);
  }

  .privacy.quiet.live {
    color: var(--accent-live);
  }

  .privacy.warn {
    color: var(--warning, #b45309);
  }

  .privacy .linkish {
    background: none;
    border: none;
    color: inherit;
    font: inherit;
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
  }

  .status-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--accent-live);
    flex-shrink: 0;
    animation: status-pulse 1.2s ease-in-out infinite;
  }

  @keyframes status-pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.35;
    }
  }
</style>
