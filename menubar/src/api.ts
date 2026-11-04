import { invoke } from "@tauri-apps/api/core";
import type { AppStatus, HomeSummary, Memory, MemoryDetail, Topic } from "./types";

interface RawMemory {
  id: string;
  body: string;
  status: string;
  app_id: string | null;
  topic_id: string | null;
  conversation_id: string | null;
  created: number;
}

interface RawTopic {
  id: string;
  title: string;
  created: number;
  memory_count: number;
  preview: string | null;
}

interface RawDetail extends RawMemory {
  topic_title: string | null;
  related: RawMemory[];
}

interface RawSummary {
  about_count: number;
  about_preview: string | null;
  topic_count: number;
  topic_preview: string | null;
  conversation_count: number;
  conversation_preview: string | null;
}

function mapMemory(raw: RawMemory): Memory {
  return {
    id: raw.id,
    body: raw.body,
    status: raw.status,
    appId: raw.app_id,
    topicId: raw.topic_id,
    conversationId: raw.conversation_id,
    created: raw.created,
  };
}

function mapTopic(raw: RawTopic): Topic {
  return {
    id: raw.id,
    title: raw.title,
    created: raw.created,
    memoryCount: raw.memory_count,
    preview: raw.preview,
  };
}

export function inTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

const CATALOG: AppStatus[] = [
  { id: "cursor", name: "Cursor", installed: true, connected: false },
  { id: "claude", name: "Claude", installed: true, connected: false },
  { id: "chatgpt", name: "ChatGPT", installed: false, connected: false },
  { id: "grok", name: "Grok", installed: true, connected: false },
  { id: "muse", name: "Muse", installed: false, connected: false },
];

const mock = {
  apps: CATALOG.map((app) => ({ ...app })),
  topics: [] as Topic[],
  memories: [] as Memory[],
  links: [] as Array<[string, string]>,
};

function uid(): string {
  return crypto.randomUUID();
}

export async function listApps(): Promise<AppStatus[]> {
  if (!inTauri()) return mock.apps.map((app) => ({ ...app }));
  return invoke<AppStatus[]>("list_apps");
}

export async function setConnected(appId: string, connected: boolean): Promise<void> {
  if (!inTauri()) {
    const app = mock.apps.find((item) => item.id === appId);
    if (!app) throw new Error("Unknown app");
    if (connected && !app.installed) throw new Error("That app is not installed");
    app.connected = connected;
    return;
  }
  await invoke("set_connected", { appId, connected });
}

export async function homeSummary(): Promise<HomeSummary> {
  if (!inTauri()) {
    const about = mock.memories.filter((memory) => !memory.topicId && !memory.conversationId);
    const connected = mock.apps.filter((app) => app.connected);
    return {
      aboutCount: about.length,
      aboutPreview: about[0]?.body ?? null,
      topicCount: mock.topics.length,
      topicPreview: mock.topics[0]?.title ?? null,
      conversationCount: connected.length,
      conversationPreview: connected[0]?.name ?? null,
    };
  }
  const raw = await invoke<RawSummary>("home_summary");
  return {
    aboutCount: raw.about_count,
    aboutPreview: raw.about_preview,
    topicCount: raw.topic_count,
    topicPreview: raw.topic_preview,
    conversationCount: raw.conversation_count,
    conversationPreview: raw.conversation_preview,
  };
}

export async function listTopics(query = ""): Promise<Topic[]> {
  if (!inTauri()) {
    const q = query.trim().toLowerCase();
    return mock.topics.filter((topic) => !q || topic.title.toLowerCase().includes(q));
  }
  const raw = await invoke<RawTopic[]>("list_topics", { query });
  return raw.map(mapTopic);
}

export async function createTopic(title: string): Promise<Topic> {
  if (!inTauri()) {
    const trimmed = title.trim();
    if (!trimmed) throw new Error("Topic needs a title");
    const topic: Topic = {
      id: uid(),
      title: trimmed,
      created: Date.now(),
      memoryCount: 0,
      preview: null,
    };
    mock.topics = [topic, ...mock.topics];
    return topic;
  }
  return mapTopic(await invoke<RawTopic>("create_topic", { title }));
}

export async function listMemories(opts: {
  query?: string;
  topicId?: string | null;
  aboutYou?: boolean;
  appId?: string | null;
  limit?: number;
}): Promise<Memory[]> {
  if (!inTauri()) {
    const q = (opts.query ?? "").trim().toLowerCase();
    return mock.memories
      .filter((memory) => !q || memory.body.toLowerCase().includes(q))
      .filter((memory) => !opts.topicId || memory.topicId === opts.topicId)
      .filter((memory) => !opts.aboutYou || (!memory.topicId && !memory.conversationId))
      .filter((memory) => !opts.appId || memory.appId === opts.appId)
      .slice(0, opts.limit ?? 50);
  }
  const raw = await invoke<RawMemory[]>("list_memories", {
    query: opts.query ?? null,
    topicId: opts.topicId ?? null,
    aboutYou: opts.aboutYou ?? false,
    appId: opts.appId ?? null,
    limit: opts.limit ?? null,
  });
  return raw.map(mapMemory);
}

export async function createMemory(body: string, topicId?: string | null, appId?: string | null): Promise<Memory> {
  if (!inTauri()) {
    const trimmed = body.trim();
    if (!trimmed) throw new Error("Memory needs a sentence");
    const memory: Memory = {
      id: uid(),
      body: trimmed,
      status: "settled",
      appId: appId ?? null,
      topicId: topicId ?? null,
      conversationId: null,
      created: Date.now(),
    };
    mock.memories = [memory, ...mock.memories];
    if (topicId) {
      const topic = mock.topics.find((item) => item.id === topicId);
      if (topic) {
        topic.memoryCount += 1;
        topic.preview = trimmed;
      }
    }
    return memory;
  }
  return mapMemory(
    await invoke<RawMemory>("create_memory", {
      body,
      topicId: topicId ?? null,
      appId: appId ?? null,
    }),
  );
}

export async function getMemory(id: string): Promise<MemoryDetail> {
  if (!inTauri()) {
    const memory = mock.memories.find((item) => item.id === id);
    if (!memory) throw new Error("Memory not found");
    const relatedIds = new Set(
      mock.links
        .filter(([from, to]) => from === id || to === id)
        .map(([from, to]) => (from === id ? to : from)),
    );
    return {
      memory,
      topicTitle: mock.topics.find((topic) => topic.id === memory.topicId)?.title ?? null,
      related: mock.memories.filter((item) => relatedIds.has(item.id)),
    };
  }
  const raw = await invoke<RawDetail>("get_memory", { id });
  return {
    memory: mapMemory(raw),
    topicTitle: raw.topic_title,
    related: raw.related.map(mapMemory),
  };
}

export async function linkMemories(fromId: string, toId: string): Promise<void> {
  if (!inTauri()) {
    if (fromId === toId) throw new Error("A memory cannot relate to itself");
    const key = [fromId, toId].sort().join(":");
    if (!mock.links.some(([from, to]) => [from, to].sort().join(":") === key)) {
      mock.links.push([fromId, toId]);
    }
    return;
  }
  await invoke("link_memories", { fromId, toId });
}

export async function openBrowse(path: string): Promise<void> {
  if (!inTauri()) {
    const url = new URL(window.location.href);
    url.searchParams.set("view", "browse");
    url.searchParams.set("path", path);
    window.location.href = url.toString();
    return;
  }
  await invoke("open_browse", { path });
}
