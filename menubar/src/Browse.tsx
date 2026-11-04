import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import {
  createMemory,
  createTopic,
  getMemory,
  homeSummary,
  inTauri,
  linkMemories,
  listApps,
  listMemories,
  listTopics,
  setConnected,
} from "./api";
import { Empty, MemoryCard, appLabel } from "./cards";
import { parseRoute, type AppStatus, type HomeSummary, type Memory, type MemoryDetail, type Route, type Topic } from "./types";

export function Browse() {
  const initial = parseRoute(new URLSearchParams(window.location.search).get("path") ?? "home");
  const [stack, setStack] = useState<Route[]>([initial]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const route = stack[stack.length - 1] ?? { name: "home" };

  useEffect(() => {
    if (!inTauri()) return;
    let unlisten: (() => void) | undefined;
    void listen<string>("navigate", (event) => {
      setStack([parseRoute(event.payload)]);
      setQuery("");
      setError("");
    }).then((fn) => {
      unlisten = fn;
    });
    return () => unlisten?.();
  }, []);

  function push(next: Route) {
    setStack((current) => [...current, next]);
    setQuery("");
    setError("");
  }

  function back() {
    setStack((current) => (current.length > 1 ? current.slice(0, -1) : [{ name: "home" }]));
    setQuery("");
    setError("");
  }

  return (
    <div className="browse">
      <header className="browse-head">
        <div className="head-row">
          {route.name === "home" ? (
            <strong>Memory</strong>
          ) : (
            <button type="button" className="text-btn" onClick={back}>
              Back
            </button>
          )}
          <button type="button" className="text-btn" onClick={() => push({ name: "connect" })}>
            Connect
          </button>
        </div>
        <input
          className="search"
          type="search"
          placeholder="Search this board"
          value={query}
          aria-label="Search this board"
          onChange={(event) => setQuery(event.target.value)}
        />
      </header>
      {error ? <p className="error">{error}</p> : null}
      <main>
        <Board
          route={route}
          query={query}
          onOpen={push}
          onError={setError}
        />
      </main>
    </div>
  );
}

function Board({
  route,
  query,
  onOpen,
  onError,
}: {
  route: Route;
  query: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  if (route.name === "home") return <HomeBoard query={query} onOpen={onOpen} onError={onError} />;
  if (route.name === "about") return <AboutBoard query={query} onOpen={onOpen} onError={onError} />;
  if (route.name === "topics") return <TopicsBoard query={query} onOpen={onOpen} onError={onError} />;
  if (route.name === "topic") {
    return <TopicBoard id={route.id} query={query} onOpen={onOpen} onError={onError} />;
  }
  if (route.name === "conversations") {
    return <ConversationsBoard onOpen={onOpen} onError={onError} />;
  }
  if (route.name === "app") return <AppBoard id={route.id} query={query} onOpen={onOpen} onError={onError} />;
  if (route.name === "memory") return <MemoryBoard id={route.id} onOpen={onOpen} onError={onError} />;
  return <ConnectBoard onError={onError} />;
}

function HomeBoard({
  query,
  onOpen,
  onError,
}: {
  query: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [summary, setSummary] = useState<HomeSummary | null>(null);
  const [hits, setHits] = useState<Memory[]>([]);

  useEffect(() => {
    let cancel = false;
    void (async () => {
      try {
        const [nextSummary, nextHits] = await Promise.all([
          homeSummary(),
          query.trim() ? listMemories({ query, limit: 20 }) : Promise.resolve([]),
        ]);
        if (!cancel) {
          setSummary(nextSummary);
          setHits(nextHits);
          onError("");
        }
      } catch (err) {
        if (!cancel) onError(err instanceof Error ? err.message : "Could not load memory");
      }
    })();
    return () => {
      cancel = true;
    };
  }, [query, onError]);

  if (query.trim()) {
    return (
      <section>
        <h1>Search</h1>
        {hits.length === 0 ? (
          <Empty title="No matches" body="Try a different word, or add a memory from the menu." />
        ) : (
          <div className="stack">
            {hits.map((memory) => (
              <MemoryCard key={memory.id} memory={memory} onOpen={() => onOpen({ name: "memory", id: memory.id })} />
            ))}
          </div>
        )}
      </section>
    );
  }

  return (
    <section>
      <h1>Memory</h1>
      <div className="category-grid">
        <button type="button" className="card category" onClick={() => onOpen({ name: "about" })}>
          <span className="kicker">Category</span>
          <strong>About you</strong>
          <p>{summary?.aboutPreview ?? "Durable facts, with no topic attached."}</p>
          <span className="count">{summary?.aboutCount ?? 0}</span>
        </button>
        <button type="button" className="card category" onClick={() => onOpen({ name: "topics" })}>
          <span className="kicker">Category</span>
          <strong>Topics</strong>
          <p>{summary?.topicPreview ?? "Clusters that come out of real use."}</p>
          <span className="count">{summary?.topicCount ?? 0}</span>
        </button>
        <button type="button" className="card category" onClick={() => onOpen({ name: "conversations" })}>
          <span className="kicker">Category</span>
          <strong>Conversations</strong>
          <p>{summary?.conversationPreview ?? "Which app a memory came from."}</p>
          <span className="count">{summary?.conversationCount ?? 0}</span>
        </button>
      </div>
    </section>
  );
}

function AboutBoard({
  query,
  onOpen,
  onError,
}: {
  query: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [draft, setDraft] = useState("");

  async function load() {
    try {
      setMemories(await listMemories({ query, aboutYou: true, limit: 100 }));
      onError("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not load memories");
    }
  }

  useEffect(() => {
    void load();
  }, [query]);

  async function onAdd(event: React.FormEvent) {
    event.preventDefault();
    try {
      await createMemory(draft);
      setDraft("");
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not save");
    }
  }

  return (
    <section>
      <h1>About you</h1>
      <form className="composer" onSubmit={(event) => void onAdd(event)}>
        <textarea
          value={draft}
          placeholder="A durable fact, like how you like to work"
          aria-label="New memory"
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit" disabled={!draft.trim()}>
          Save
        </button>
      </form>
      {memories.length === 0 ? (
        <Empty title="No personal memories yet" body="Facts you save here stay separate from a topic." />
      ) : (
        <div className="stack">
          {memories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} onOpen={() => onOpen({ name: "memory", id: memory.id })} />
          ))}
        </div>
      )}
    </section>
  );
}

function TopicsBoard({
  query,
  onOpen,
  onError,
}: {
  query: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [title, setTitle] = useState("");

  async function load() {
    try {
      setTopics(await listTopics(query));
      onError("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not load topics");
    }
  }

  useEffect(() => {
    void load();
  }, [query]);

  async function onAdd(event: React.FormEvent) {
    event.preventDefault();
    try {
      const topic = await createTopic(title);
      setTitle("");
      onOpen({ name: "topic", id: topic.id });
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not create topic");
    }
  }

  return (
    <section>
      <h1>Topics</h1>
      <form className="composer inline" onSubmit={(event) => void onAdd(event)}>
        <input
          value={title}
          placeholder="New topic"
          aria-label="New topic"
          onChange={(event) => setTitle(event.target.value)}
        />
        <button type="submit" disabled={!title.trim()}>
          Add
        </button>
      </form>
      {topics.length === 0 ? (
        <Empty title="No topics yet" body="A topic is a card, like Coffee or a project name. It is not a folder." />
      ) : (
        <div className="card-grid">
          {topics.map((topic) => (
            <button
              key={topic.id}
              type="button"
              className="card category"
              onClick={() => onOpen({ name: "topic", id: topic.id })}
            >
              <strong>{topic.title}</strong>
              <p>{topic.preview ?? "No memories in this topic yet."}</p>
              <span className="count">{topic.memoryCount}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function TopicBoard({
  id,
  query,
  onOpen,
  onError,
}: {
  id: string;
  query: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [title, setTitle] = useState("Topic");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [draft, setDraft] = useState("");

  async function load() {
    try {
      const [topics, next] = await Promise.all([
        listTopics(""),
        listMemories({ query, topicId: id, limit: 100 }),
      ]);
      setTitle(topics.find((topic) => topic.id === id)?.title ?? "Topic");
      setMemories(next);
      onError("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not load topic");
    }
  }

  useEffect(() => {
    void load();
  }, [id, query]);

  async function onAdd(event: React.FormEvent) {
    event.preventDefault();
    try {
      await createMemory(draft, id);
      setDraft("");
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not save");
    }
  }

  return (
    <section>
      <h1>{title}</h1>
      <form className="composer" onSubmit={(event) => void onAdd(event)}>
        <textarea
          value={draft}
          placeholder="Add a memory to this topic"
          aria-label="New memory"
          onChange={(event) => setDraft(event.target.value)}
        />
        <button type="submit" disabled={!draft.trim()}>
          Save
        </button>
      </form>
      {memories.length === 0 ? (
        <Empty title="Empty topic" body="Save a sentence and it will show up as a card." />
      ) : (
        <div className="stack">
          {memories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} onOpen={() => onOpen({ name: "memory", id: memory.id })} />
          ))}
        </div>
      )}
    </section>
  );
}

function ConversationsBoard({
  onOpen,
  onError,
}: {
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [apps, setApps] = useState<AppStatus[]>([]);

  useEffect(() => {
    void listApps()
      .then((next) => {
        setApps(next.filter((app) => app.connected));
        onError("");
      })
      .catch((err: unknown) => onError(err instanceof Error ? err.message : "Could not load apps"));
  }, [onError]);

  return (
    <section>
      <h1>Conversations</h1>
      {apps.length === 0 ? (
        <Empty
          title="No apps connected"
          body="Connect Cursor, Claude, ChatGPT, Grok, or Muse. Memories from those apps will land on a card here."
        />
      ) : (
        <div className="card-grid">
          {apps.map((app) => (
            <button
              key={app.id}
              type="button"
              className="card category"
              onClick={() => onOpen({ name: "app", id: app.id })}
            >
              <span className="kicker">App</span>
              <strong>{app.name}</strong>
              <p>Memories from {app.name} will show up here once the link exists.</p>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function AppBoard({
  id,
  query,
  onOpen,
  onError,
}: {
  id: AppStatus["id"];
  query: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const name = appLabel(id) ?? id;

  useEffect(() => {
    void listMemories({ query, appId: id, limit: 100 })
      .then((next) => {
        setMemories(next);
        onError("");
      })
      .catch((err: unknown) => onError(err instanceof Error ? err.message : "Could not load memories"));
  }, [id, query, onError]);

  return (
    <section>
      <h1>{name}</h1>
      {memories.length === 0 ? (
        <Empty title="Nothing from this app yet" body={`Memories from ${name} will land here once the link exists.`} />
      ) : (
        <div className="stack">
          {memories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} onOpen={() => onOpen({ name: "memory", id: memory.id })} />
          ))}
        </div>
      )}
    </section>
  );
}

function MemoryBoard({
  id,
  onOpen,
  onError,
}: {
  id: string;
  onOpen: (route: Route) => void;
  onError: (message: string) => void;
}) {
  const [detail, setDetail] = useState<MemoryDetail | null>(null);
  const [others, setOthers] = useState<Memory[]>([]);
  const [relateTo, setRelateTo] = useState("");

  async function load() {
    try {
      const [next, pool] = await Promise.all([getMemory(id), listMemories({ limit: 100 })]);
      setDetail(next);
      setOthers(pool.filter((memory) => memory.id !== id));
      onError("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not load memory");
    }
  }

  useEffect(() => {
    void load();
  }, [id]);

  async function onRelate(event: React.FormEvent) {
    event.preventDefault();
    if (!relateTo) return;
    try {
      await linkMemories(id, relateTo);
      setRelateTo("");
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not link memories");
    }
  }

  if (!detail) return null;
  const { memory, topicTitle, related } = detail;
  const source = appLabel(memory.appId);

  return (
    <section>
      <article className="card detail">
        <p className="sentence">{memory.body}</p>
        <p className="meta">
          {memory.status}
          {source ? ` · ${source}` : ""}
        </p>
        <div className="links">
          {memory.topicId && topicTitle ? (
            <button type="button" className="chip on" onClick={() => onOpen({ name: "topic", id: memory.topicId! })}>
              {topicTitle}
            </button>
          ) : (
            <button type="button" className="chip" onClick={() => onOpen({ name: "about" })}>
              About you
            </button>
          )}
          {memory.appId ? (
            <button
              type="button"
              className="chip"
              onClick={() => onOpen({ name: "app", id: memory.appId as AppStatus["id"] })}
            >
              {source}
            </button>
          ) : null}
        </div>
      </article>

      <h2>Related</h2>
      {related.length === 0 ? (
        <p className="quiet">No related memories yet.</p>
      ) : (
        <div className="stack">
          {related.map((item) => (
            <MemoryCard key={item.id} memory={item} onOpen={() => onOpen({ name: "memory", id: item.id })} />
          ))}
        </div>
      )}

      {others.length > 0 ? (
        <form className="composer inline" onSubmit={(event) => void onRelate(event)}>
          <select value={relateTo} aria-label="Related memory" onChange={(event) => setRelateTo(event.target.value)}>
            <option value="">Relate to another memory</option>
            {others.map((item) => (
              <option key={item.id} value={item.id}>
                {item.body}
              </option>
            ))}
          </select>
          <button type="submit" disabled={!relateTo}>
            Link
          </button>
        </form>
      ) : null}
    </section>
  );
}

function ConnectBoard({ onError }: { onError: (message: string) => void }) {
  const [apps, setApps] = useState<AppStatus[]>([]);

  async function load() {
    try {
      setApps(await listApps());
      onError("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not detect apps");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function toggle(app: AppStatus) {
    try {
      await setConnected(app.id, !app.connected);
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Could not update connection");
    }
  }

  return (
    <section>
      <h1>Connect</h1>
      <p className="lead">Choose the apps on this Mac. Connecting records the choice. It does not write their settings yet.</p>
      <div className="card-grid">
        {apps.map((app) => (
          <article key={app.id} className="card app-card">
            <strong>{app.name}</strong>
            <p>{app.installed ? "Installed" : "Not found"}</p>
            <button type="button" disabled={!app.installed} onClick={() => void toggle(app)}>
              {app.connected ? "Connected" : "Connect"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
