<script lang="ts">
  import { api } from "$lib/api";
  import { assistant, isIdleSession } from "$lib/stores/assistant.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { classifyIntent, leftoverQuestionAfterTeach, shouldAutoResearch } from "$lib/assistant/intent";
  import { suggestTopicName } from "$lib/assistant/topic-name";
  import { ensureProjectFolder, readNote, updateProjectFolder } from "$lib/vault/load";
  import { splitFrontmatter } from "$lib/vault/markdown";
  import { tabs } from "$lib/stores/tabs.svelte";
  import type { ManagerJob } from "$lib/api";
  import type { ChatStarterId, ChatSetupAction } from "$lib/assistant/chat-starters";
  import { composerPlaceholder, landingPhase } from "$lib/assistant/chat-starters";
  import { THIN_MEMORY_REFUSE } from "$lib/assistant/composer-skills";
  import { channelComposerPlaceholder } from "$lib/assistant/channel-agents";
  import ComposerDock from "./ComposerDock.svelte";
  import ChatLanding from "./ChatLanding.svelte";
  import ChatThread from "./ChatThread.svelte";
  import RunDetailsDrawer from "./RunDetailsDrawer.svelte";
  import TopicPicker from "./TopicPicker.svelte";
  import { folderLabel, pathsMatch } from "$lib/assistant/workspace-chats";
  import { fade, fly } from "svelte/transition";
  import { cubicOut } from "svelte/easing";

  let noteExcerpt = $state("");
  let groqConfigured = $state(false);
  let llmProvider = $state("groq");
  let llmConfigured = $state(false);

  const noteTitle = $derived(
    workspace.activeNotePath?.split("/").pop()?.replace(/\.md$/, "") ?? null,
  );
  const offline = $derived(!connection.connected);
  const aiConfigured = $derived(
    llmProvider === "ollama" || llmConfigured || groqConfigured,
  );
  const libraryReady = $derived(connection.collectionCount > 0);
  const hasWorkspace = $derived(workspace.projectFolders.length > 0);
  const channelEmpty = $derived(workspace.channelEmpty);
  const bootstrap = $derived(offline || !aiConfigured || !hasWorkspace);
  const phase = $derived(
    landingPhase({ offline, aiConfigured, hasWorkspace, libraryReady, channelEmpty }),
  );
  const onboarding = $derived(!bootstrap && channelEmpty);
  const landingPlaceholder = $derived(composerPlaceholder(phase));
  const agentPlaceholder = $derived(channelComposerPlaceholder(onboarding));
  const needsSetup = $derived(!connection.connected || !aiConfigured);
  const thread = $derived(assistant.getActiveThread());
  const empty = $derived(isIdleSession({ turns: thread }));
  /** Idle chat → Cursor-style centered composer; after first send → dock. */
  const showNewChat = $derived(empty);
  const showSetupLanding = $derived(empty && phase !== "ready");
  const newChatPlaceholder = $derived(
    offline
      ? "Backend offline — reconnect to send…"
      : showSetupLanding
        ? landingPlaceholder
        : "Teach, ask from memory, or start research…",
  );
  const missionTurn = $derived(assistant.getMissionTurn());
  const showDetails = $derived(
    assistant.inspectorOpen &&
      missionTurn != null &&
      assistant.viewMode !== "report" &&
      (missionTurn.status === "done" ||
        !!missionTurn.livePlan ||
        (missionTurn.liveQueries?.length ?? 0) > 0 ||
        missionTurn.status === "running" ||
        missionTurn.status === "awaiting_plan"),
  );

  async function loadNoteExcerpt(path: string | null) {
    if (!path || !path.endsWith(".md")) {
      noteExcerpt = "";
      return;
    }
    try {
      noteExcerpt = splitFrontmatter(await readNote(path)).body.slice(0, 2000);
    } catch {
      noteExcerpt = "";
    }
  }

  async function loadSetupStatus() {
    if (!connection.connected) return;
    try {
      const settings = await api.getSettings();
      groqConfigured = settings.groq_configured;
      llmConfigured = settings.llm_configured ?? settings.groq_configured;
      llmProvider = settings.llm_provider || settings.values.LLM_PROVIDER || "groq";
    } catch {
      groqConfigured = false;
      llmConfigured = false;
    }
  }

  $effect(() => {
    void loadNoteExcerpt(workspace.activeNotePath);
  });
  $effect(() => {
    if (connection.connected) void loadSetupStatus();
  });

  async function chatContext() {
    const parts: string[] = [];
    if (noteExcerpt) parts.push(noteExcerpt);
    for (const a of assistant.attachments) {
      if (a.text?.trim()) {
        parts.push(`Attached ${a.name}:\n${a.text.trim().slice(0, 4000)}`);
        continue;
      }
      if (a.path && /\.(md|txt)$/i.test(a.path)) {
        try {
          const body = splitFrontmatter(await readNote(a.path)).body;
          parts.push(`Attached ${a.name}:\n${body.slice(0, 4000)}`);
        } catch {
          parts.push(`Attached ${a.name}`);
        }
        continue;
      }
      parts.push(`Attached file ${a.name}.`);
    }
    return {
      note_path: workspace.activeNotePath,
      selected_text: workspace.selectedText || null,
      note_excerpt: parts.join("\n\n").slice(0, 8000) || null,
    };
  }

  async function explain(question: string, sessionId?: string | null) {
    const ctx = await chatContext();
    await assistant.sendQuickAnswer(workspace.activeNotePath, ctx, question, {
      sessionId: sessionId ?? assistant.activeSessionId,
    });
  }

  async function retryAsk(turnId: string) {
    const ctx = await chatContext();
    await assistant.retryQuickAnswer(turnId, ctx);
  }

  async function bindTopic(
    suggested?: string | null,
    sessionId?: string | null,
  ): Promise<string | null> {
    const sid = sessionId ?? assistant.activeSessionId;
    const existing = sid
      ? (assistant.sessions[sid]?.projectPath ?? null)
      : assistant.activeProjectPath();
    if (existing) return existing;
    const name = (suggested || "").trim() || "Research";
    try {
      const path = await ensureProjectFolder(name);
      assistant.setSessionProject(path, sid ?? undefined);
      await workspace.syncProjectsFromDisk();
      return path;
    } catch {
      assistant.appendManager("Couldn't create a topic folder for this.", sid);
      return null;
    }
  }

  async function retargetTopic(name: string): Promise<string | null> {
    const clean = (name || "").trim() || "Research";
    try {
      const path = await ensureProjectFolder(clean);
      assistant.setSessionProject(path);
      await workspace.syncProjectsFromDisk();
      return path;
    } catch {
      assistant.appendManager("Couldn't switch this chat to that topic folder.");
      return null;
    }
  }

  function resolveFolder(name: string): { name: string; path: string } | null {
    const n = name.trim().toLowerCase();
    if (!n) return null;
    const folders = workspace.projectFolders;
    const exact = folders.find((f) => f.name.toLowerCase() === n);
    if (exact) return exact;
    const hits = folders.filter(
      (f) => f.name.toLowerCase().includes(n) || n.includes(f.name.toLowerCase()),
    );
    return hits.length === 1 ? hits[0] : null;
  }

  function alsoPathsFromTurn(names: string[], paths: string[]): string[] {
    const bound = assistant.activeProjectPath();
    const out: string[] = [];
    for (const p of paths) {
      if (p && p !== bound && !out.includes(p)) out.push(p);
    }
    for (const name of names) {
      const hit = resolveFolder(name);
      if (hit && hit.path !== bound && !out.includes(hit.path)) out.push(hit.path);
    }
    return out;
  }

  async function submitTurn(raw?: string) {
    const text = (raw ?? assistant.input).trim();
    const hasAttachments = assistant.attachments.length > 0;
    if (!text && !hasAttachments) return;

    const sessionId =
      assistant.activeSessionId ??
      (workspace.activeTopicPath
        ? tabs.newChatInWorkspace(workspace.activeTopicPath)
        : null);
    if (!sessionId) return;

    // Lock before any await — otherwise Enter key-repeat / double-click can
    // run manager+answer twice for the same composer message.
    if (!assistant.beginPendingTurn(sessionId)) return;
    assistant.input = "";

    const clarifyCount = assistant.clarifyCount();
    const history = assistant.managerHistory();

    let kind: "ask" | "dispatch" = "dispatch";
    let job: ManagerJob = "answer";
    let refuseMessage = "";
    let instruction = text;
    let managerText = "";
    let createTopic = "";
    let retargetTopicName = "";
    let mergeSource = "";
    let mergeDest = "";
    let alsoTopics: string[] = [];
    let alsoFromTurn: string[] = [];
    let newTopic = "";
    let idea = "";
    const forcedSkill = assistant.forcedJob;

    try {
      try {
        const turn = await api.managerTurn({
          message: text,
          projectPath: assistant.sessions[sessionId]?.projectPath ?? assistant.activeProjectPath(),
          sessionId,
          hasAttachments,
          clarifyCount,
          history,
          topics: workspace.projectFolders.map((f) => ({ name: f.name, path: f.path })),
          forcedJob: forcedSkill,
        });
        kind = turn.kind;
        job = (turn.job ?? "answer") as ManagerJob;
        refuseMessage = turn.refuse_message || "";
        instruction = turn.instruction || text;
        managerText = turn.text || "";
        createTopic = turn.create_topic || "";
        retargetTopicName = turn.retarget_topic || "";
        mergeSource = turn.merge_source || "";
        mergeDest = turn.merge_dest || "";
        alsoTopics = turn.also_topics || [];
        alsoFromTurn = turn.also_project_paths || [];
        newTopic = turn.new_topic || "";
        idea = turn.idea || "";
        // One-shot force: clear after a successful route so Auto resumes
        if (assistant.forcedJob) assistant.setForcedJob(null);
      } catch {
        const intent = classifyIntent({ text, hasAttachments });
        job =
          shouldAutoResearch(text) || forcedSkill === "research"
            ? "research"
            : intent === "teach"
              ? "file"
              : intent === "lookup"
                ? "research"
                : "answer";
        createTopic = suggestTopicName(text);
      }

      if (kind === "ask") {
        assistant.appendUser(text || "Attached files", sessionId);
        assistant.appendManager(managerText, sessionId);
        assistant.bumpClarify();
        return;
      }

      const inInterview = clarifyCount > 0;
      if (!inInterview) assistant.appendUser(text || (hasAttachments ? "Files" : ""), sessionId);
      else assistant.appendUser(text, sessionId);
      assistant.resetInterview();
      if (managerText && job !== "refuse") {
        assistant.appendManager(managerText, sessionId);
      }
      if (idea.trim()) await persistIdea(idea);

      if (job === "retarget") {
        await retargetTopic(retargetTopicName || createTopic || instruction);
        return;
      }
      if (job === "split") {
        const name = newTopic || createTopic || instruction || "Research";
        const path = await ensureProjectFolder(name);
        await workspace.syncProjectsFromDisk();
        tabs.newSessionTab({ projectPath: path });
        assistant.appendManager(`This chat writes to ${name}.`, sessionId);
        return;
      }
      if (job === "merge") {
        const src = resolveFolder(mergeSource);
        const destName = mergeDest || "Research";
        const destPath = (resolveFolder(destName)?.path ?? (await ensureProjectFolder(destName)));
        if (!src) {
          assistant.appendManager(
            `I don't have a folder named ${mergeSource} to combine.`,
            sessionId,
          );
          return;
        }
        try {
          const result = await api.mergeMemory({
            sourceProjectPath: src.path,
            destProjectPath: destPath,
          });
          await workspace.syncProjectsFromDisk();
          assistant.setSessionProject(destPath, sessionId);
          assistant.appendManager(
            `Copied ${result.copied} claim(s) into ${result.dest_name}. ${src.name} is still on disk.`,
            sessionId,
          );
        } catch (e) {
          assistant.appendManager(
            e instanceof Error ? e.message : "Couldn't combine those topics.",
            sessionId,
          );
        }
        return;
      }
      if (kind !== "ask") {
        await bindTopic(createTopic || suggestTopicName(instruction || text), sessionId);
      }

      if (job === "watch") {
        const project =
          assistant.sessions[sessionId]?.projectPath ?? assistant.activeProjectPath();
        if (!project) {
          assistant.appendManager(
            "I need a topic folder before I can start scheduled research.",
            sessionId,
          );
          return;
        }
        try {
          const created = await api.createWatch(project, {
            name: instruction.slice(0, 48) || "Scheduled Research",
            focus: instruction,
            enabled: true,
          });
          const status = created.enabled
            ? "It's Active — refine Exclude/Trusted sources or hit Run anytime."
            : "Fill Focus and Include in Scheduled Research, then turn it Active.";
          assistant.appendManager(
            `Schedule created — open Scheduled Research to refine or Run. ${status}`,
            sessionId,
          );
          if (created.watch_id && created.enabled) {
            void api.cloudWatchSync(created.project_path, created.watch_id).catch(() => {});
          }
          app.openWatch();
        } catch (e) {
          assistant.appendManager(
            e instanceof Error ? e.message : "Couldn't start scheduled research.",
            sessionId,
          );
        }
        return;
      }

      if (job === "file") {
        const followUp = leftoverQuestionAfterTeach(text);
        await assistant.runDigest({
          text: followUp ? "" : instruction || undefined,
          sessionId,
        });
        if (followUp) await explain(followUp, sessionId);
        return;
      }
      const alsoPaths = alsoPathsFromTurn(alsoTopics, alsoFromTurn);
      if (job === "research") {
        await assistant.runGoal(instruction, {
          skipUserTurn: true,
          alsoProjectPaths: alsoPaths,
          sessionId,
        });
        return;
      }
      if (job === "refuse") {
        if (shouldAutoResearch(text) || forcedSkill === "research") {
          await assistant.runGoal(instruction || text, {
            skipUserTurn: true,
            alsoProjectPaths: alsoPaths,
            sessionId,
          });
          return;
        }
        assistant.presentRefuse(text, refuseMessage || THIN_MEMORY_REFUSE, {
          skipUserTurn: true,
          sessionId,
        });
        return;
      }
      if (shouldAutoResearch(instruction || text)) {
        await assistant.runGoal(instruction || text, {
          skipUserTurn: true,
          alsoProjectPaths: alsoPaths,
          sessionId,
        });
        return;
      }
      await assistant.sendQuickAnswer(workspace.activeNotePath, await chatContext(), instruction, {
        skipUserTurn: true,
        alsoProjectPaths: alsoPaths,
        sessionId,
      });
    } finally {
      assistant.endPendingTurn(sessionId);
    }
  }

  function submit() {
    void submitTurn();
  }

  async function persistIdea(idea: string) {
    const path = assistant.activeProjectPath() ?? workspace.activeTopicPath;
    if (!path || !idea.trim()) return;
    try {
      await updateProjectFolder(path, { idea: idea.trim() });
      await workspace.refreshChannelEmpty();
    } catch {
      assistant.appendManager("Couldn't save IDEA.md for this workspace.");
    }
  }

  async function lookupInResearch(query: string) {
    await assistant.runGoal(query, { skipUserTurn: false });
  }

  function openPath(path: string) {
    app.openDocument(path, { from: "agent" });
    workspace.setActiveNote(path);
  }

  const topicPath = $derived(
    assistant.activeProjectPath() ?? workspace.activeTopicPath ?? "",
  );
  const topicLabel = $derived(folderLabel(topicPath) || "Choose workspace");

  /** Bind this new chat to a workspace and keep the sidebar on that folder. */
  function selectTopic(path: string) {
    if (!path) {
      if (assistant.activeSessionId) assistant.setSessionProject(null);
      return;
    }

    const sid = assistant.activeSessionId;
    const session = sid ? assistant.sessions[sid] : null;

    // Idle new chat: rebind in place so draft text/attachments stay put.
    if (session && isIdleSession(session)) {
      if (!pathsMatch(session.projectPath, path)) {
        assistant.setSessionProject(path, sid);
      } else {
        workspace.setActiveTopic(path);
      }
      tabs.ensureSessionTab(sid);
      app.openHome();
      return;
    }

    // No open session (empty workspace) — open a new chat there.
    tabs.newChatInWorkspace(path);
  }

  $effect(() => {
    if (bootstrap) return;
    if (!channelEmpty) return;
    assistant.ensureManagerOpener(true);
  });

  function applyStarter(prompt: string, id: ChatStarterId) {
    const jobs = {
      teach: "file",
      ask: "answer",
      research: "research",
      watch: "watch",
    } as const;
    assistant.setForcedJob(jobs[id]);
    assistant.input = prompt;
    assistant.composerFocusNonce += 1;
  }

  function openSetupAction(action: ChatSetupAction) {
    if (action === "import" || action === "ingest") {
      app.openSheet("ingest");
      return;
    }
    if (action === "workspace") {
      app.openNewProject();
      return;
    }
    if (action === "reindex") {
      void connection.retryReindex();
      return;
    }
    app.openSheet("settings");
  }
</script>

{#snippet workspacePicker()}
  <TopicPicker
    value={topicPath}
    label={topicLabel}
    allowCreate
    searchPlaceholder="Search workspaces…"
    onSelect={selectTopic}
    onNewWorkspace={() => app.openNewProject()}
  />
{/snippet}

<div class="agent-pane" class:empty={showNewChat} data-testid="pane-center">
  {#if !showNewChat && needsSetup}
    <div class="banner">
      <span>Set up AI to start.</span>
      <button type="button" class="link" onclick={() => app.openSheet("settings")}>Settings</button>
    </div>
  {:else if !showNewChat && connection.memorySearchBlocked}
    <div class="banner">
      {#if connection.reindexBusy}
        <span>Rebuilding search index…</span>
      {:else if connection.reindexError}
        <span>{connection.reindexError}</span>
        <button type="button" class="link" onclick={() => void connection.retryReindex()}>
          Retry
        </button>
      {:else if connection.reindexRequired}
        <span>Updating search index…</span>
      {:else}
        <span>
          {connection.embeddingsError || "Vault search is temporarily unavailable."}
        </span>
        <button type="button" class="link" onclick={() => void connection.retryReindex()}>
          Retry
        </button>
      {/if}
    </div>
  {/if}

  {#if showNewChat}
    <div
      class="new-chat-stage"
      data-testid="agent-landing"
      in:fade={{ duration: 180, easing: cubicOut }}
      out:fade={{ duration: 140, easing: cubicOut }}
    >
      <div class="new-chat-inner">
        {#if showSetupLanding}
          <ChatLanding
            {phase}
            topicLabel={topicLabel}
            {offline}
            {aiConfigured}
            {hasWorkspace}
            libraryReady={libraryReady}
            {channelEmpty}
            memoryBlocked={connection.memorySearchBlocked}
            disabled={offline || assistant.isLoading}
            onStarter={applyStarter}
            onSetupAction={openSetupAction}
            onNewWorkspace={() => app.openNewProject()}
          >
            {#snippet compose()}
              <ComposerDock
                {offline}
                {noteTitle}
                variant="center"
                placeholder={newChatPlaceholder}
                header={workspacePicker}
                onSubmit={submit}
              />
            {/snippet}
          </ChatLanding>
        {:else}
          <div
            class="new-chat-compose"
            in:fly={{ y: 10, duration: 220, easing: cubicOut }}
          >
            <ComposerDock
              {offline}
              {noteTitle}
              variant="center"
              placeholder={newChatPlaceholder}
              header={workspacePicker}
              onSubmit={submit}
            />
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <div
      class="stage-row"
      in:fade={{ duration: 180, easing: cubicOut }}
    >
      <div class="stage-area">
        <ChatThread
          onOpenPath={openPath}
          onCancel={() => assistant.cancelResearch()}
          onLookup={(query) => void lookupInResearch(query)}
          onRetryAsk={(id) => void retryAsk(id)}
          onTeach={() => {
            assistant.setForcedJob("file");
            assistant.input = "";
            assistant.composerFocusNonce += 1;
          }}
          onViewMemory={() => app.openMemory()}
        />
      </div>

      {#if showDetails && missionTurn}
        <RunDetailsDrawer
          plan={missionTurn.livePlan ?? ""}
          queries={missionTurn.liveQueries ?? []}
          critiqueHistory={missionTurn.liveCritiqueHistory?.length
            ? missionTurn.liveCritiqueHistory
            : (missionTurn.result?.critique_history ?? [])}
          result={missionTurn.result ?? null}
          confidence={missionTurn.confidence ?? missionTurn.result?.confidence ?? undefined}
          goalStatus={missionTurn.goalStatus ?? missionTurn.result?.goal_status ?? ""}
          runMode={missionTurn.runMode ?? "studio"}
          savedPath={missionTurn.savedPath ?? missionTurn.result?.report_path ?? undefined}
          learningPath={missionTurn.learningPath ?? missionTurn.result?.learning_path ?? undefined}
          indexed={missionTurn.indexed ?? false}
          memoryDetail={missionTurn.memoryDetail ?? ""}
          claimCount={missionTurn.claimCount ?? missionTurn.result?.claim_count ?? 0}
          sessionId={assistant.activeSessionId}
          onOpenPath={openPath}
          onClose={() => {
            if (assistant.inspectorOpen) assistant.toggleInspector();
          }}
        />
      {/if}
    </div>

    <div in:fly={{ y: 16, duration: 240, easing: cubicOut }}>
      <ComposerDock
        {offline}
        {noteTitle}
        variant="dock"
        placeholder={agentPlaceholder}
        onSubmit={submit}
      />
    </div>
  {/if}
</div>

<style>
  .agent-pane {
    flex: 1;
    min-height: 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    position: relative;
    --chat-gutter: 1.5rem;
    --chat-col: 42rem;
  }

  .banner {
    flex-shrink: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 0.75rem;
    align-items: center;
    padding: 0.45rem 0.75rem;
    background: var(--warning-dim);
    border-bottom: 1px solid var(--border-subtle);
    font-size: var(--text-sm);
    color: var(--text);
  }

  .link {
    background: none;
    border: none;
    color: var(--accent-link);
    font-size: var(--text-sm);
    cursor: pointer;
    padding: 0;
    min-height: auto;
  }

  .stage-row {
    flex: 1 1 auto;
    display: flex;
    min-height: 0;
  }

  .stage-area {
    flex: 1 1 auto;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .agent-pane :global(.dock-wrap.dock) {
    flex-shrink: 0;
    width: 100%;
  }

  .agent-pane.empty {
    --chat-col: 44rem;
  }

  .new-chat-stage {
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem 1.25rem 2.5rem;
  }

  .new-chat-inner {
    width: 100%;
    max-width: var(--chat-col, 40rem);
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .new-chat-compose {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    width: 100%;
  }
</style>
