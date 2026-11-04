import type { Memory } from "./types";

const APP_LABEL: Record<string, string> = {
  cursor: "Cursor",
  claude: "Claude",
  chatgpt: "ChatGPT",
  grok: "Grok",
  muse: "Muse",
};

export function appLabel(id: string | null): string | null {
  if (!id) return null;
  return APP_LABEL[id] ?? id;
}

export function MemoryCard({ memory, onOpen }: { memory: Memory; onOpen: () => void }) {
  const source = appLabel(memory.appId);
  return (
    <button type="button" className="card memory-card" onClick={onOpen}>
      <p>{memory.body}</p>
      <span className="meta">
        <span className="pill">{memory.status}</span>
        {source ? <span className="pill">{source}</span> : null}
      </span>
    </button>
  );
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      <p className="quiet">{body}</p>
    </div>
  );
}
