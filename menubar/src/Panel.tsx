import { useEffect, useState } from "react";
import { createMemory, listApps, listMemories, openBrowse } from "./api";
import { MemoryCard } from "./cards";
import type { AppStatus, Memory } from "./types";

export function Panel() {
  const [apps, setApps] = useState<AppStatus[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  async function refresh(nextQuery = query) {
    try {
      const [nextApps, nextMemories] = await Promise.all([
        listApps(),
        listMemories({ query: nextQuery, limit: 8 }),
      ]);
      setApps(nextApps);
      setMemories(nextMemories);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load memory");
    } finally {
      setReady(true);
    }
  }

  useEffect(() => {
    void refresh(query);
    const onFocus = () => void refresh(query);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [query]);

  async function onAdd(event: React.FormEvent) {
    event.preventDefault();
    try {
      await createMemory(draft);
      setDraft("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  }

  const connected = apps.filter((app) => app.connected);

  return (
    <div className="panel">
      <header className="panel-head">
        <strong>Memory</strong>
        <button type="button" className="text-btn" onClick={() => void openBrowse("home")}>
          Browse
        </button>
      </header>

      <div className="chips">
        {connected.length === 0 ? (
          <button type="button" className="chip" onClick={() => void openBrowse("connect")}>
            Connect an app
          </button>
        ) : (
          connected.map((app) => (
            <button
              key={app.id}
              type="button"
              className="chip on"
              onClick={() => void openBrowse(`app:${app.id}`)}
            >
              {app.name}
            </button>
          ))
        )}
      </div>

      <input
        className="search"
        type="search"
        placeholder="Search memory"
        value={query}
        aria-label="Search memory"
        onChange={(event) => setQuery(event.target.value)}
      />

      <form className="add" onSubmit={(event) => void onAdd(event)}>
        <input
          value={draft}
          placeholder="Add a memory"
          aria-label="Add a memory"
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit" disabled={!draft.trim()}>
          Save
        </button>
      </form>

      {error ? <p className="error" role="alert">{error}</p> : null}

      <p className="kicker panel-label">Recent</p>
      <div className="list">
        {!ready ? (
          <p className="loading">Loading memory…</p>
        ) : memories.length === 0 ? (
          <p className="quiet">Nothing saved yet.</p>
        ) : (
          memories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              onOpen={() => void openBrowse(`memory:${memory.id}`)}
            />
          ))
        )}
      </div>
    </div>
  );
}
