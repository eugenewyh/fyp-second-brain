export type AppId = "cursor" | "claude" | "chatgpt" | "grok" | "muse";

export interface AppStatus {
  id: AppId;
  name: string;
  installed: boolean;
  connected: boolean;
}

export interface Topic {
  id: string;
  title: string;
  created: number;
  memoryCount: number;
  preview: string | null;
}

export interface Memory {
  id: string;
  body: string;
  status: string;
  appId: string | null;
  topicId: string | null;
  conversationId: string | null;
  created: number;
}

export interface MemoryDetail {
  memory: Memory;
  topicTitle: string | null;
  related: Memory[];
}

export interface HomeSummary {
  aboutCount: number;
  aboutPreview: string | null;
  topicCount: number;
  topicPreview: string | null;
  conversationCount: number;
  conversationPreview: string | null;
}

export type Route =
  | { name: "home" }
  | { name: "about" }
  | { name: "topics" }
  | { name: "topic"; id: string }
  | { name: "conversations" }
  | { name: "app"; id: AppId }
  | { name: "memory"; id: string }
  | { name: "connect" };

export function parseRoute(path: string): Route {
  if (path === "about") return { name: "about" };
  if (path === "topics") return { name: "topics" };
  if (path === "conversations") return { name: "conversations" };
  if (path === "connect") return { name: "connect" };
  if (path.startsWith("topic:")) return { name: "topic", id: path.slice(6) };
  if (path.startsWith("app:")) return { name: "app", id: path.slice(4) as AppId };
  if (path.startsWith("memory:")) return { name: "memory", id: path.slice(7) };
  return { name: "home" };
}

export function routePath(route: Route): string {
  switch (route.name) {
    case "home":
      return "home";
    case "about":
      return "about";
    case "topics":
      return "topics";
    case "topic":
      return `topic:${route.id}`;
    case "conversations":
      return "conversations";
    case "app":
      return `app:${route.id}`;
    case "memory":
      return `memory:${route.id}`;
    case "connect":
      return "connect";
  }
}
