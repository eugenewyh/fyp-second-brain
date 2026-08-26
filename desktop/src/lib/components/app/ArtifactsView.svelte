<script lang="ts">
  import { onMount } from "svelte";
  import { api, type DigestListItem } from "$lib/api";
  import { assistant } from "$lib/stores/assistant.svelte";
  import { app } from "$lib/stores/app.svelte";
  import { connection } from "$lib/stores/connection.svelte";
  import { FileText, Link2, ExternalLink, CalendarCheck } from "@lucide/svelte";

  type Filter = "all" | "files" | "links" | "digests";

  type Artifact = {
    key: string;
    title: string;
    location: string;
    sessionTitle: string;
    updatedAt: number;
    kind: "file" | "link" | "digest";
    path?: string;
    url?: string;
    sessionId?: string;
    turnId?: string;
  };

  let filter = $state<Filter>(app.artifactsFilter);
  let query = $state("");
  let digests = $state<DigestListItem[]>([]);

  $effect(() => {
    if (app.isArtifacts) {
      filter = app.artifactsFilter;
    }
  });

  const missionArtifacts = $derived.by((): Artifact[] => {
    const out: Artifact[] = [];
    for (const m of assistant.listResearchMissions()) {
      const session = assistant.sessions[m.sessionId];
      const turn = session?.turns.find((t) => t.id === m.turnId);
      const paths = new Set<string>();
      if (m.savedPath) paths.add(m.savedPath);
      if (turn?.kind === "research" && turn.result) {
        const r = turn.result;
        if (r.saved_path) paths.add(r.saved_path);
        if (r.report_path) paths.add(r.report_path);
        if (r.learning_path) paths.add(r.learning_path);
        for (const line of r.retrieval_log ?? []) {
          const urlMatch = line.match(/https?:\/\/\S+/i);
          if (urlMatch) {
            const url = urlMatch[0].replace(/[),.;]+$/, "");
            out.push({
              key: `link:${m.turnId}:${url}`,
              title: url.replace(/^https?:\/\//, "").slice(0, 64),
              location: url,
              sessionTitle: m.sessionTitle,
              updatedAt: m.updatedAt,
              kind: "link",
              url,
              sessionId: m.sessionId,
              turnId: m.turnId,
            });
          }
        }
      }
      for (const p of paths) {
        out.push({
          key: `file:${m.turnId}:${p}`,
          title: p.split(/[\\/]/).pop() ?? p,
          location: p,
          sessionTitle: m.sessionTitle,
          updatedAt: m.updatedAt,
          kind: "file",
          path: p,
          sessionId: m.sessionId,
          turnId: m.turnId,
        });
      }
      if (paths.size === 0 && m.query) {
        out.push({
          key: `mission:${m.turnId}`,
          title: m.query,
          location: m.runMode === "goal" ? "Goal run" : "Research run",
          sessionTitle: m.sessionTitle,
          updatedAt: m.updatedAt,
          kind: "file",
          sessionId: m.sessionId,
          turnId: m.turnId,
        });
      }
    }
    return out;
  });

  const digestArtifacts = $derived.by((): Artifact[] =>
    digests.map((d) => ({
      key: `digest:${d.date}`,
      title: `Daily brief · ${d.date}`,
      location: d.path,
      sessionTitle:
        d.learnings > 0
          ? `${d.learnings} learning${d.learnings === 1 ? "" : "s"}`
          : d.summary?.slice(0, 48) || "Digest",
      updatedAt: Date.parse(`${d.date}T12:00:00`) || 0,
      kind: "digest" as const,
      path: d.path,
    })),
  );

  const artifacts = $derived.by((): Artifact[] => {
    return [...missionArtifacts, ...digestArtifacts].sort(
      (a, b) => b.updatedAt - a.updatedAt,
    );
  });

  const filtered = $derived(
    artifacts.filter((a) => {
      if (filter === "files" && a.kind !== "file") return false;
      if (filter === "links" && a.kind !== "link") return false;
      if (filter === "digests" && a.kind !== "digest") return false;
      if (!query.trim()) return true;
      const q = query.trim().toLowerCase();
      return (
        a.title.toLowerCase().includes(q) ||
        a.location.toLowerCase().includes(q) ||
        a.sessionTitle.toLowerCase().includes(q)
      );
    }),
  );

  function formatWhen(ts: number): string {
    try {
      return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(ts));
    } catch {
      return new Date(ts).toLocaleString();
    }
  }

  function openItem(a: Artifact) {
    if (a.url && typeof window !== "undefined") {
      window.open(a.url, "_blank", "noopener,noreferrer");
      return;
    }
    if (a.path) {
      app.openDocument(a.path, {
        label: a.kind === "digest" ? a.title : undefined,
        from: "artifacts",
      });
      return;
    }
    if (a.turnId && a.sessionId) {
      assistant.openMissionView(a.turnId, a.sessionId);
    }
  }

  async function loadDigests() {
    if (!connection.connected) return;
    try {
      const res = await api.listDigests(40);
      digests = res.digests;
    } catch {
      digests = [];
    }
  }

  onMount(() => {
    void loadDigests();
  });

  $effect(() => {
    if (connection.connected) void loadDigests();
  });
</script>

<div class="artifacts" data-testid="artifacts-view">
  <header class="top" data-tauri-drag-region>
    <input
      class="search"
      type="search"
      placeholder="Search artifacts…"
      bind:value={query}
    />
    <div class="filters" role="tablist">
      <button
        type="button"
        class="f"
        class:active={filter === "all"}
        onclick={() => (filter = "all")}
      >
        All {artifacts.length}
      </button>
      <button
        type="button"
        class="f"
        class:active={filter === "files"}
        onclick={() => (filter = "files")}
      >
        Files
      </button>
      <button
        type="button"
        class="f"
        class:active={filter === "links"}
        onclick={() => (filter = "links")}
      >
        Links
      </button>
      <button
        type="button"
        class="f"
        class:active={filter === "digests"}
        onclick={() => (filter = "digests")}
      >
        Digests {digests.length}
      </button>
    </div>
  </header>

  {#if filtered.length === 0}
    <div class="empty">
      <p class="empty-title">No artifacts yet</p>
      <p class="empty-sub">
        Reports, daily digests, and sources from goals and research appear here.
      </p>
    </div>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Title / name</th>
            <th>Location</th>
            <th>Session</th>
          </tr>
        </thead>
        <tbody>
          {#each filtered as a (a.key)}
            <tr>
              <td>
                <button type="button" class="row-btn" onclick={() => openItem(a)}>
                  <span class="ico">
                    {#if a.kind === "link"}
                      <Link2 size={14} strokeWidth={1.75} />
                    {:else if a.kind === "digest"}
                      <CalendarCheck size={14} strokeWidth={1.75} />
                    {:else}
                      <FileText size={14} strokeWidth={1.75} />
                    {/if}
                  </span>
                  <span class="name">{a.title}</span>
                  {#if a.url}
                    <span class="ext"><ExternalLink size={12} strokeWidth={1.75} /></span>
                  {/if}
                </button>
              </td>
              <td class="loc" title={a.location}>{a.location}</td>
              <td class="sess">
                <div class="sess-title">{a.sessionTitle}</div>
                <div class="sess-when">{formatWhen(a.updatedAt)}</div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .artifacts {
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--bg);
  }

  .top {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0 1.25rem;
    min-height: var(--titlebar-height);
    flex-shrink: 0;
    position: relative;
    z-index: 5;
    -webkit-app-region: drag;
    app-region: drag;
  }
  .top :global(input),
  .top :global(button) {
    -webkit-app-region: no-drag;
    app-region: no-drag;
  }

  .search {
    flex: 1;
    max-width: 22rem;
    height: 34px;
    padding: 0 0.75rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
    color: var(--text);
    font-size: var(--text-sm);
  }

  .search:focus {
    outline: none;
    border-color: var(--border-active);
    box-shadow: 0 0 0 3px var(--focus-ring);
  }

  .filters {
    display: flex;
    gap: 0.25rem;
    margin-left: auto;
  }

  .f {
    background: transparent;
    border: none;
    color: var(--text-faint);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    min-height: 30px;
    padding: 0.25rem 0.65rem;
    border-radius: var(--radius-feedback);
    cursor: pointer;
  }

  .f.active {
    color: var(--text);
    box-shadow: inset 0 -2px 0 0 var(--accent-live);
  }

  .empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 2rem;
  }

  .empty-title {
    font-size: var(--text-md);
    font-weight: var(--font-semibold);
    color: var(--text);
  }

  .empty-sub {
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .table-wrap {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th {
    text-align: left;
    font-size: var(--text-2xs);
    font-weight: var(--font-semibold);
    letter-spacing: var(--type-caption-tracking);
    text-transform: uppercase;
    color: var(--text-faint);
    padding: 0.55rem 1.25rem;
    border-bottom: 1px solid var(--border-subtle);
    position: sticky;
    top: 0;
    background: var(--bg-elevated);
  }

  td {
    padding: 0.55rem 1.25rem;
    border-bottom: 1px solid var(--border-subtle);
    font-size: var(--text-sm);
    color: var(--text-muted);
    vertical-align: middle;
  }

  .row-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: none;
    border: none;
    padding: 0;
    color: var(--text);
    cursor: pointer;
    text-align: left;
    max-width: 100%;
  }

  .row-btn:hover .name {
    color: var(--accent-live);
  }

  .ico {
    display: inline-flex;
    color: var(--text-faint);
    flex-shrink: 0;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ext {
    display: inline-flex;
    color: var(--text-faint);
  }

  .loc {
    max-width: 18rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--font-mono);
    font-size: var(--text-2xs);
  }

  .sess-title {
    color: var(--text-muted);
    font-size: var(--text-sm);
  }

  .sess-when {
    color: var(--text-faint);
    font-size: var(--text-2xs);
  }
</style>
