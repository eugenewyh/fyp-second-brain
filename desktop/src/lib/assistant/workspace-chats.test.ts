import { describe, expect, it } from "vitest";
import {
  chatsForWorkspace,
  folderLabel,
  formatRelativeTime,
  groupSessionsByWorkspace,
  lastChatInWorkspace,
  pathsMatch,
  type WorkspaceSession,
} from "./workspace-chats";

const dlm = "/vault/dlm";
const grpo = "/vault/JustGRPO";

const sessions: WorkspaceSession[] = [
  { id: "a", title: "Speed vs JSON", projectPath: dlm, updatedAt: 30 },
  { id: "b", title: "Find papers on JustGRPO", projectPath: grpo, updatedAt: 40 },
  { id: "c", title: "DiffusionGemma notes", projectPath: `${dlm}/`, updatedAt: 50 },
  { id: "d", title: "Unbound", projectPath: null, updatedAt: 90 },
];

describe("pathsMatch", () => {
  it("treats trailing slashes as the same folder", () => {
    expect(pathsMatch(dlm, `${dlm}/`)).toBe(true);
    expect(pathsMatch(dlm, grpo)).toBe(false);
    expect(pathsMatch(null, dlm)).toBe(false);
  });
});

describe("folderLabel", () => {
  it("uses the last path segment", () => {
    expect(folderLabel(dlm)).toBe("dlm");
    expect(folderLabel("/vault/JustGRPO")).toBe("JustGRPO");
    expect(folderLabel(null)).toBe("");
  });
});

describe("chatsForWorkspace", () => {
  it("keeps only that folder and sorts newest first", () => {
    const hits = chatsForWorkspace(sessions, dlm);
    expect(hits.map((s) => s.id)).toEqual(["c", "a"]);
  });

  it("returns nothing for an empty or missing workspace", () => {
    expect(chatsForWorkspace(sessions, "/vault/empty")).toEqual([]);
    expect(chatsForWorkspace(sessions, null)).toEqual([]);
  });

  it("hides unbound chats", () => {
    expect(chatsForWorkspace(sessions, dlm).some((s) => s.id === "d")).toBe(false);
  });

  it("filters by title", () => {
    expect(chatsForWorkspace(sessions, dlm, "json").map((s) => s.id)).toEqual(["a"]);
  });
});

describe("lastChatInWorkspace", () => {
  it("returns the most recently updated chat", () => {
    expect(lastChatInWorkspace(sessions, dlm)?.id).toBe("c");
    expect(lastChatInWorkspace(sessions, "/vault/missing")).toBeNull();
  });
});

const folders = [
  { name: "dlm", path: dlm },
  { name: "JustGRPO", path: grpo },
  { name: "empty", path: "/vault/empty" },
];

describe("groupSessionsByWorkspace", () => {
  it("groups chats under each workspace folder", () => {
    const groups = groupSessionsByWorkspace(sessions, folders);
    expect(groups.map((g) => g.path)).toEqual([dlm, grpo, "/vault/empty"]);
    expect(groups[0].sessions.map((s) => s.id)).toEqual(["c", "a"]);
    expect(groups[1].sessions.map((s) => s.id)).toEqual(["b"]);
    expect(groups[2].sessions).toEqual([]);
    expect(groups.every((g) => g.pinned === false)).toBe(true);
  });

  it("filters chat titles across workspaces", () => {
    const groups = groupSessionsByWorkspace(sessions, folders, "json");
    expect(groups[0].sessions.map((s) => s.id)).toEqual(["a"]);
    expect(groups[1].sessions).toEqual([]);
  });

  it("sorts pinned workspaces first", () => {
    const groups = groupSessionsByWorkspace(sessions, folders, "", [grpo]);
    expect(groups.map((g) => g.path)).toEqual([grpo, dlm, "/vault/empty"]);
    expect(groups[0].pinned).toBe(true);
  });

  it("orders multiple pins by most-recently-pinned first", () => {
    const groups = groupSessionsByWorkspace(sessions, folders, "", [grpo, dlm]);
    expect(groups.map((g) => g.path)).toEqual([grpo, dlm, "/vault/empty"]);
    expect(groups.filter((g) => g.pinned).map((g) => g.path)).toEqual([grpo, dlm]);
  });
});

describe("formatRelativeTime", () => {
  const now = Date.UTC(2026, 7, 24, 12, 0, 0);

  it("uses short relative labels", () => {
    expect(formatRelativeTime(now - 30_000, now)).toBe("now");
    expect(formatRelativeTime(now - 5 * MS_MIN, now)).toBe("5m");
    expect(formatRelativeTime(now - 2 * MS_HOUR, now)).toBe("2h");
    expect(formatRelativeTime(now - 3 * MS_DAY, now)).toBe("3d");
  });
});

const MS_MIN = 60_000;
const MS_HOUR = 3_600_000;
const MS_DAY = 86_400_000;
