import { api, type ChatContext, type ChatMessage, type Source } from "$lib/api";
import { connection } from "$lib/stores/connection.svelte";

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

class ChatStore {
  threads = $state<Record<string, ChatTurn[]>>({});
  loading = $state(false);
  lastSources = $state<Source[]>([]);
  error = $state("");

  threadKey(notePath: string | null): string {
    return notePath ?? "__global__";
  }

  getThread(notePath: string | null): ChatTurn[] {
    return this.threads[this.threadKey(notePath)] ?? [];
  }

  clearThread(notePath: string | null) {
    const key = this.threadKey(notePath);
    const { [key]: _, ...rest } = this.threads;
    this.threads = rest;
    this.lastSources = [];
    this.error = "";
  }

  async send(
    notePath: string | null,
    content: string,
    context: ChatContext,
  ): Promise<void> {
    const trimmed = content.trim();
    if (!trimmed) return;

    const key = this.threadKey(notePath);
    const prior = this.getThread(notePath);
    const userTurn: ChatTurn = { role: "user", content: trimmed };
    this.threads = { ...this.threads, [key]: [...prior, userTurn] };
    this.loading = true;
    this.error = "";

    const messages: ChatMessage[] = [...prior, userTurn].map((t) => ({
      role: t.role,
      content: t.content,
    }));

    try {
      const result = await api.chat(messages, context);
      const assistantTurn: ChatTurn = {
        role: "assistant",
        content: result.answer,
        sources: result.sources,
      };
      this.threads = {
        ...this.threads,
        [key]: [...this.getThread(notePath), assistantTurn],
      };
      this.lastSources = result.sources;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Chat failed";
      this.error = message;
      connection.connectionError = message;
    } finally {
      this.loading = false;
    }
  }
}

export const chat = new ChatStore();