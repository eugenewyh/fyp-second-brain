/** Chats that belong to the open Cursor-style workspace (one vault folder). */

export type WorkspaceSession = {
  id: string;
  title: string;
  projectPath: string | null;
  updatedAt: number;
};

export type WorkspaceGroup = {
  path: string;
  name: string;
  sessions: WorkspaceSession[];
  pinned: boolean;
};

export function pathsMatch(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  if (!a || !b) return false;
  const na = a.replace(/[/\\]+$/, "").toLowerCase();
  const nb = b.replace(/[/\\]+$/, "").toLowerCase();
  return na === nb;
}

export function folderLabel(path: string | null | undefined): string {
  if (!path?.trim()) return "";
  return path.split(/[/\\]/).pop()?.replace(/[-_]/g, " ") ?? "";
}

/** Sessions in this workspace, newest first. Unbound sessions are excluded. */
export function chatsForWorkspace(
  sessions: WorkspaceSession[],
  workspacePath: string | null,
  query = "",
): WorkspaceSession[] {
  if (!workspacePath) return [];
  const q = query.trim().toLowerCase();
  return sessions
    .filter((s) => pathsMatch(s.projectPath, workspacePath))
    .filter((s) => !q || (s.title || "").toLowerCase().includes(q))
    .slice()
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

export function lastChatInWorkspace(
  sessions: WorkspaceSession[],
  workspacePath: string | null,
): WorkspaceSession | null {
  return chatsForWorkspace(sessions, workspacePath)[0] ?? null;
}

/** One folder row per disk workspace with its chats (newest first). Pinned first (pin order). */
export function groupSessionsByWorkspace(
  sessions: WorkspaceSession[],
  projectFolders: { name: string; path: string }[],
  query = "",
  pinnedPaths: string[] = [],
): WorkspaceGroup[] {
  const pinRank = new Map(
    pinnedPaths.map((p, i) => [p.replace(/[/\\]+$/, "").toLowerCase(), i]),
  );
  const folderRank = new Map(
    projectFolders.map((folder, i) => [
      folder.path.replace(/[/\\]+$/, "").toLowerCase(),
      i,
    ]),
  );
  const groups = projectFolders.map((folder) => ({
    path: folder.path,
    name: folder.name,
    sessions: chatsForWorkspace(sessions, folder.path, query),
    pinned: pinnedPaths.some((p) => pathsMatch(p, folder.path)),
  }));
  return groups.sort((a, b) => {
    if (a.pinned !== b.pinned) return Number(b.pinned) - Number(a.pinned);
    if (a.pinned && b.pinned) {
      const ra =
        pinRank.get(a.path.replace(/[/\\]+$/, "").toLowerCase()) ?? Number.MAX_SAFE_INTEGER;
      const rb =
        pinRank.get(b.path.replace(/[/\\]+$/, "").toLowerCase()) ?? Number.MAX_SAFE_INTEGER;
      return ra - rb;
    }
    const fa =
      folderRank.get(a.path.replace(/[/\\]+$/, "").toLowerCase()) ?? Number.MAX_SAFE_INTEGER;
    const fb =
      folderRank.get(b.path.replace(/[/\\]+$/, "").toLowerCase()) ?? Number.MAX_SAFE_INTEGER;
    return fa - fb;
  });
}

const MS_MIN = 60_000;
const MS_HOUR = 3_600_000;
const MS_DAY = 86_400_000;

/** Cursor-style short relative time for sidebar chat rows. */
export function formatRelativeTime(updatedAt: number, now = Date.now()): string {
  const delta = Math.max(0, now - updatedAt);
  if (delta < MS_MIN) return "now";
  if (delta < MS_HOUR) return `${Math.floor(delta / MS_MIN)}m`;
  if (delta < MS_DAY) return `${Math.floor(delta / MS_HOUR)}h`;
  if (delta < MS_DAY * 7) return `${Math.floor(delta / MS_DAY)}d`;
  try {
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
      new Date(updatedAt),
    );
  } catch {
    return new Date(updatedAt).toLocaleDateString();
  }
}
