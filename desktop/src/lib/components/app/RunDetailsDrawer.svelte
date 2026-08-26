<script lang="ts">
  import type { CritiqueHistoryEntry, ResearchResult } from "$lib/api";
  import SectionHeader from "$lib/ui/SectionHeader.svelte";
  import Badge from "$lib/ui/Badge.svelte";
  import SelfCritiquePanel from "$lib/components/mission/SelfCritiquePanel.svelte";
  import { workspace } from "$lib/stores/workspace.svelte";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { readNote } from "$lib/vault/load";

  interface Props {
    plan?: string;
    queries?: string[];
    critiqueHistory?: CritiqueHistoryEntry[];
    result?: ResearchResult | null;
    confidence?: number;
    goalStatus?: string;
    runMode?: "studio" | "goal";
    savedPath?: string;
    learningPath?: string;
    indexed?: boolean;
    memoryDetail?: string;
    claimCount?: number;
    sessionId?: string | null;
    onOpenPath?: (path: string) => void;
    onClose?: () => void;
  }

  let {
    plan = "",
    queries = [],
    critiqueHistory = [],
    result = null,
    confidence,
    goalStatus = "",
    runMode = "studio",
    savedPath,
    learningPath,
    indexed = false,
    memoryDetail = "",
    claimCount = 0,
    sessionId = null,
    onOpenPath,
    onClose,
  }: Props = $props();

  let chatMemoryPeek = $state("");
  let projectBelievesPeek = $state("");

  const queryBullets = $derived(queries.slice(0, 5));
  const planPreview = $derived.by(() => {
    const t = plan.trim();
    if (!t) return "";
    const first = t.split(/\n+/).map((l) => l.trim()).filter(Boolean)[0] ?? "";
    return first.length > 180 ? first.slice(0, 177) + "…" : first;
  });
  const confLabel = $derived(
    confidence == null || Number.isNaN(confidence)
      ? null
      : `${Math.round(confidence * 100)}%`,
  );
  const latestCritique = $derived.by(() => {
    const hist = critiqueHistory.length
      ? critiqueHistory
      : (result?.critique_history ?? []);
    const last = hist[hist.length - 1];
    const c = last?.critique;
    if (c?.summary) return { verdict: c.verdict ?? "", summary: c.summary.slice(0, 280) };
    if (result?.critique) {
      return {
        verdict: result.critique_approved ? "approved" : "revise",
        summary: String(result.critique).slice(0, 280),
      };
    }
    return null;
  });

  const projectRoot = $derived(assistant.activeProjectPath());
  const projectMemoryPath = $derived.by(() => {
    if (!projectRoot) return null;
    return `${projectRoot.replace(/\/$/, "")}/memory/project.md`;
  });
  const chatMemoryPath = $derived.by(() => {
    const sid = sessionId || assistant.activeSessionId;
    if (!projectRoot || !sid) return null;
    return `${projectRoot.replace(/\/$/, "")}/memory/agents/${sid}/memory.md`;
  });
  const claimsDirHint = $derived.by(() => {
    if (!projectRoot) return null;
    return `${projectRoot.replace(/\/$/, "")}/memory/claims`;
  });

  function sectionBullets(raw: string, heading: string, max = 8): string {
    const re = new RegExp(
      `##\\s*${heading.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`,
      "i",
    );
    const m = raw.match(re);
    if (!m) return "";
    const lines = m[1]!
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.startsWith("- ") && !l.includes("(none yet)"));
    return lines.slice(0, max).join("\n");
  }

  async function loadMemoryPeeks() {
    chatMemoryPeek = "";
    projectBelievesPeek = "";
    if (chatMemoryPath) {
      try {
        const raw = await readNote(chatMemoryPath);
        const lines = raw
          .split("\n")
          .map((l) => l.trim())
          .filter((l) => l.startsWith("- "));
        chatMemoryPeek = lines.slice(-8).join("\n");
      } catch {
        chatMemoryPeek = "";
      }
    }
    if (projectMemoryPath) {
      try {
        const raw = await readNote(projectMemoryPath);
        projectBelievesPeek =
          sectionBullets(raw, "Settled claims") ||
          raw
            .split("\n")
            .map((l) => l.trim())
            .filter((l) => l.startsWith("- "))
            .slice(-8)
            .join("\n");
      } catch {
        projectBelievesPeek = "";
      }
    }
  }

  $effect(() => {
    void workspace.vaultRefreshNonce;
    void chatMemoryPath;
    void projectMemoryPath;
    void loadMemoryPeeks();
  });
</script>

<aside class="details ui-scroll" data-testid="run-details-drawer" aria-label="Run details">
  <div class="head">
    <SectionHeader title="Details" subtitle={runMode === "goal" ? "Goal run" : "Research run"} mono />
    {#if onClose}
      <button type="button" class="close" onclick={onClose}>Hide</button>
    {/if}
  </div>

  <section class="block">
    <h4>Plan</h4>
    {#if queryBullets.length}
      <ol class="queries">
        {#each queryBullets as q}
          <li>{q.replace(/^\[(personal|web|arxiv)\]\s*/i, "").trim() || q}</li>
        {/each}
      </ol>
      {#if queries.length > queryBullets.length}
        <p class="more">+{queries.length - queryBullets.length} more</p>
      {/if}
    {:else if planPreview}
      <p class="plan-one">{planPreview}</p>
    {:else}
      <p class="empty">Plan appears when the planner finishes.</p>
    {/if}
  </section>

  <section class="block compact-critique">
    {#if latestCritique}
      <div class="verdict-row">
        <span class="lbl">Self-critique</span>
        <Badge variant={latestCritique.verdict === "approved" ? "success" : "warning"}>
          {latestCritique.verdict || "—"}
        </Badge>
      </div>
      <p class="summary">{latestCritique.summary}</p>
    {:else}
      <SelfCritiquePanel history={critiqueHistory} {result} />
    {/if}
  </section>

  <section class="block">
    <h4>Summary</h4>
    <ul class="meta">
      {#if confLabel}
        <li>Confidence {confLabel}</li>
      {/if}
      {#if goalStatus}
        <li>{goalStatus}</li>
      {/if}
      {#if memoryDetail}
        <li>{memoryDetail}</li>
      {/if}
      {#if (result?.contested_claims?.length ?? 0) > 0}
        <li>
          Contested with your notes:
          {(result?.contested_claims ?? [])
            .map((c) => c.claim)
            .filter(Boolean)
            .slice(0, 2)
            .join(" · ")}
        </li>
      {/if}
      {#if claimCount > 0}
        <li>{claimCount} claim{claimCount === 1 ? "" : "s"} written</li>
      {/if}
      {#if indexed}
        <li>Indexed in project memory</li>
      {/if}
    </ul>
    <div class="links">
      {#if savedPath}
        <button type="button" class="link" onclick={() => onOpenPath?.(savedPath!)}>
          Open report
        </button>
      {/if}
      {#if learningPath}
        <button type="button" class="link" onclick={() => onOpenPath?.(learningPath!)}>
          Open learning
        </button>
      {/if}
    </div>
  </section>

  <section class="block">
    <h4>This chat remembers</h4>
    {#if chatMemoryPeek}
      <pre class="peek">{chatMemoryPeek}</pre>
    {:else}
      <p class="empty">Chat memory appears after a run saves learnings.</p>
    {/if}
    {#if chatMemoryPath}
      <button type="button" class="link" onclick={() => onOpenPath?.(chatMemoryPath!)}>
        Open chat memory
      </button>
    {/if}
  </section>

  <section class="block">
    <h4>Project believes</h4>
    {#if projectBelievesPeek}
      <pre class="peek">{projectBelievesPeek}</pre>
    {:else}
      <p class="empty">Settled claims appear in project.md after runs.</p>
    {/if}
    <div class="links">
      {#if projectMemoryPath}
        <button type="button" class="link" onclick={() => onOpenPath?.(projectMemoryPath!)}>
          Open project.md
        </button>
      {/if}
      {#if claimsDirHint}
        <button
          type="button"
          class="link"
          onclick={() => onOpenPath?.(projectMemoryPath || claimsDirHint!)}
          title={claimsDirHint}
        >
          Claims live under memory/claims
        </button>
      {/if}
    </div>
  </section>
</aside>

<style>
  .details {
    flex: 0 0 280px;
    width: 280px;
    min-height: 0;
    overflow-y: auto;
    border-left: 1px solid var(--border-subtle);
    background: var(--bg-elevated);
    padding: 0.85rem 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  @media (max-width: 1100px) {
    .details {
      display: none;
    }
  }

  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .close {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    color: var(--text-muted);
    padding: 0.25rem 0.5rem;
    cursor: pointer;
  }

  .block h4 {
    margin: 0 0 0.4rem;
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
  }

  .queries {
    margin: 0;
    padding-left: 1.1rem;
    font-size: var(--text-sm);
    color: var(--text);
    line-height: 1.45;
  }

  .queries li {
    margin-bottom: 0.3rem;
  }

  .more,
  .empty,
  .plan-one {
    margin: 0.35rem 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .verdict-row {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.35rem;
  }

  .lbl {
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
    text-transform: uppercase;
    letter-spacing: var(--type-caption-tracking);
    color: var(--text-faint);
  }

  .summary {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text);
    line-height: 1.45;
    white-space: pre-wrap;
  }

  .meta {
    list-style: none;
    margin: 0;
    padding: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .link {
    background: none;
    border: none;
    color: var(--accent-link);
    font-size: var(--text-sm);
    cursor: pointer;
    padding: 0;
    text-align: left;
  }

  .peek {
    margin: 0 0 0.45rem;
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    line-height: 1.45;
    color: var(--text-muted);
    white-space: pre-wrap;
    max-height: 9rem;
    overflow: auto;
  }

  .compact-critique :global(.critique-panel) {
    margin: 0;
  }
</style>
