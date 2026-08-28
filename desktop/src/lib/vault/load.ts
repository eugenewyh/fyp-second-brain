import { invoke } from "@tauri-apps/api/core";
import { readDir, readTextFile, writeTextFile, exists, mkdir, rename, remove } from "@tauri-apps/plugin-fs";
import type { VaultNode } from "./types";
import { channelLooksEmpty } from "$lib/assistant/channel-empty";
import { isRememberableNotePath } from "$lib/vault/rememberable";
import {
  filterUserSubfolders,
  folderNameFromPath,
  ideaBodyFromMarkdown,
  ideaMarkdownFromBody,
  parentDir,
} from "./project-edit";

const SUPPORTED_EXTENSIONS = new Set([".md", ".txt", ".pdf"]);

export async function getProjectRoot(): Promise<string> {
  try {
    return await invoke<string>("get_project_root");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Vault root unavailable: ${message}`);
  }
}

export async function getVaultRoot(): Promise<string> {
  const root = await getProjectRoot();
  return `${root}/data/documents`;
}

async function buildTree(dirPath: string): Promise<VaultNode[]> {
  const entries = await readDir(dirPath);
  const nodes: VaultNode[] = [];

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    const fullPath = `${dirPath}/${entry.name}`;
    if (entry.isDirectory) {
      const children = await buildTree(fullPath);
      if (children.length > 0) {
        nodes.push({ name: entry.name, path: fullPath, type: "folder", children });
      }
    } else {
      const ext = entry.name.includes(".") ? `.${entry.name.split(".").pop()}` : "";
      if (SUPPORTED_EXTENSIONS.has(ext.toLowerCase())) {
        nodes.push({ name: entry.name, path: fullPath, type: "file" });
      }
    }
  }

  nodes.sort((a, b) => {
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  return nodes;
}

export async function loadVaultTree(root?: string): Promise<VaultNode[]> {
  const vaultRoot = root ?? (await getVaultRoot());
  if (!(await exists(vaultRoot))) {
    await mkdir(vaultRoot, { recursive: true });
    return [];
  }
  return buildTree(vaultRoot);
}

/** Top-level vault folders as projects (includes empty folders). */
export async function listProjectFolders(
  root?: string,
): Promise<{ name: string; path: string }[]> {
  const vaultRoot = root ?? (await getVaultRoot());
  if (!(await exists(vaultRoot))) {
    await mkdir(vaultRoot, { recursive: true });
    return [];
  }
  const entries = await readDir(vaultRoot);
  const folders: { name: string; path: string }[] = [];
  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    if (!entry.isDirectory) continue;
    folders.push({ name: entry.name, path: `${vaultRoot}/${entry.name}` });
  }
  folders.sort((a, b) => a.name.localeCompare(b.name));
  return folders;
}

/** Subfolder under a new project: empty create, or copy from an existing local path. */
export type ProjectFolderSpec =
  | { kind: "create"; name: string }
  | { kind: "import"; name: string; sourcePath: string };

export type CreateProjectOptions = {
  /** Free-form idea written to IDEA.md */
  idea?: string;
  /**
   * Subfolders under the project.
   * Accepts legacy string names or structured create/import specs.
   */
  folders?: Array<string | ProjectFolderSpec>;
};

function sanitizeFolderName(raw: string): string {
  return raw.replace(/[\\/]/g, "-").trim();
}

function uniqueChildName(used: Set<string>, base: string): string {
  let name = base || "folder";
  if (!used.has(name.toLowerCase())) {
    used.add(name.toLowerCase());
    return name;
  }
  let i = 2;
  while (used.has(`${name} (${i})`.toLowerCase())) i += 1;
  name = `${name} (${i})`;
  used.add(name.toLowerCase());
  return name;
}

function normalizeFolderSpecs(
  folders: Array<string | ProjectFolderSpec> | undefined,
  alreadyUsed?: Iterable<string>,
): ProjectFolderSpec[] {
  if (!folders?.length) return [];
  const used = new Set(
    alreadyUsed ? [...alreadyUsed].map((s) => s.toLowerCase()) : [],
  );
  const out: ProjectFolderSpec[] = [];
  for (const raw of folders) {
    if (typeof raw === "string") {
      const name = sanitizeFolderName(raw);
      if (!name) continue;
      out.push({ kind: "create", name: uniqueChildName(used, name) });
      continue;
    }
    const name = sanitizeFolderName(raw.name);
    if (!name) continue;
    const unique = uniqueChildName(used, name);
    if (raw.kind === "import" && raw.sourcePath) {
      out.push({ kind: "import", name: unique, sourcePath: raw.sourcePath });
    } else {
      out.push({ kind: "create", name: unique });
    }
  }
  return out;
}

/** Copy a local directory into the vault under dest (must stay under data/documents). */
export async function copyDirIntoVault(sourcePath: string, destPath: string): Promise<string> {
  return invoke<string>("copy_dir_into_vault", {
    source: sourcePath,
    dest: destPath,
  });
}

/** Create a top-level project folder under the vault (with a starter note so it appears in trees). */
export async function createProjectFolder(
  name: string,
  opts?: CreateProjectOptions,
): Promise<string> {
  const clean = name.replace(/[\\/]/g, "-").trim();
  if (!clean) throw new Error("Project name required");
  const vaultRoot = await getVaultRoot();
  if (!(await exists(vaultRoot))) {
    await mkdir(vaultRoot, { recursive: true });
  }
  const path = `${vaultRoot}/${clean}`;
  if (await exists(path)) {
    throw new Error(`Project “${clean}” already exists`);
  }
  await mkdir(path, { recursive: true });
  const readme = `${path}/README.md`;
  await writeTextFile(readme, `# ${clean}\n\nProject notes and sources.\n`);
  const idea = opts?.idea?.trim();
  if (idea) {
    await writeTextFile(`${path}/IDEA.md`, `# Idea\n\n${idea}\n`);
  }
  const specs = normalizeFolderSpecs(opts?.folders);
  for (const spec of specs) {
    const dest = `${path}/${spec.name}`;
    if (spec.kind === "import") {
      await copyDirIntoVault(spec.sourcePath, dest);
    } else {
      await mkdir(dest, { recursive: true });
    }
  }
  return path;
}

/** Create a project folder, or reuse one with the same name. Manager-owned topics. */
export async function ensureProjectFolder(name: string): Promise<string> {
  const clean = name.replace(/[\\/]/g, "-").trim() || "Research";
  const existing = (await listProjectFolders()).find(
    (p) => p.name.toLowerCase() === clean.toLowerCase(),
  );
  if (existing) return existing.path;
  try {
    return await createProjectFolder(clean);
  } catch {
    const again = (await listProjectFolders()).find(
      (p) => p.name.toLowerCase() === clean.toLowerCase(),
    );
    if (again) return again.path;
    throw new Error(`Could not create topic “${clean}”`);
  }
}

/** Folders reserved for system output — not user projects. */
const SYSTEM_PROJECT_NAMES = new Set(["research", "memory"]);

const SEED_FLAG = "sb-default-project-seeded";

function hasSeededDefaultProject(): boolean {
  if (typeof localStorage === "undefined") return false;
  try {
    return localStorage.getItem(SEED_FLAG) === "1";
  } catch {
    return false;
  }
}

function markSeededDefaultProject(): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(SEED_FLAG, "1");
  } catch {
    /* ignore */
  }
}

/**
 * Resolve user projects. Seeds "Inbox" **once** on first run only.
 * Does not recreate Inbox after the user deletes it.
 * Returns a project path, or null if the vault has no user projects.
 */
export async function ensureDefaultProject(root?: string): Promise<string | null> {
  const vaultRoot = root ?? (await getVaultRoot());
  if (!(await exists(vaultRoot))) {
    await mkdir(vaultRoot, { recursive: true });
  }
  // Ensure system dirs exist (not user projects)
  for (const sys of ["research", "memory/learnings"]) {
    const p = `${vaultRoot}/${sys}`;
    if (!(await exists(p))) await mkdir(p, { recursive: true });
  }

  const projects = (await listProjectFolders(vaultRoot)).filter(
    (p) => !SYSTEM_PROJECT_NAMES.has(p.name.toLowerCase()),
  );
  if (projects.length > 0) {
    markSeededDefaultProject();
    const inbox = projects.find((p) => p.name.toLowerCase() === "inbox");
    return (inbox ?? projects[0]).path;
  }

  // First-run seed only — never resurrect after user deletes all projects
  if (!hasSeededDefaultProject()) {
    const path = await createProjectFolder("Inbox");
    markSeededDefaultProject();
    return path;
  }
  return null;
}

/** True if path is a directory under the vault (project folder still exists). */
export async function projectPathExists(path: string | null | undefined): Promise<boolean> {
  if (!path) return false;
  try {
    return await exists(path);
  } catch {
    return false;
  }
}

export async function readNote(path: string): Promise<string> {
  return readTextFile(path);
}

export async function writeNote(path: string, content: string): Promise<void> {
  const parent = path.substring(0, path.lastIndexOf("/"));
  if (parent && !(await exists(parent))) {
    await mkdir(parent, { recursive: true });
  }
  await writeTextFile(path, content);
}

export async function readProjectIdea(path: string): Promise<string> {
  const file = `${path}/IDEA.md`;
  if (!(await exists(file))) return "";
  try {
    return ideaBodyFromMarkdown(await readTextFile(file));
  } catch {
    return "";
  }
}

async function collectNotePaths(dirPath: string, acc: string[] = []): Promise<string[]> {
  let entries: Awaited<ReturnType<typeof readDir>> = [];
  try {
    entries = await readDir(dirPath);
  } catch {
    return acc;
  }
  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    const fullPath = `${dirPath}/${entry.name}`;
    if (entry.isDirectory) {
      await collectNotePaths(fullPath, acc);
    } else {
      acc.push(fullPath);
    }
  }
  return acc;
}

/** True when this topic folder has no IDEA, claims, or rememberable notes. */
export async function channelIsEmpty(path: string | null | undefined): Promise<boolean> {
  if (!path) return false;
  try {
    if (!(await exists(path))) return false;
  } catch {
    return false;
  }
  const idea = await readProjectIdea(path);
  const claimCount = await countTopicClaims(path);
  const notePaths = await collectNotePaths(path);
  return channelLooksEmpty({ idea, claimCount, notePaths });
}

/** Settled memory cards under `{topic}/memory/claims`. */
export async function countTopicClaims(path: string | null | undefined): Promise<number> {
  if (!path) return 0;
  const claimsDir = `${path}/memory/claims`;
  try {
    if (!(await exists(claimsDir))) return 0;
    const entries = await readDir(claimsDir);
    return entries.filter((e) => !e.isDirectory && e.name.endsWith(".md")).length;
  } catch {
    return 0;
  }
}

/**
 * Notes on disk that Ask cannot use yet — files exist, but no memory claims.
 * Dumping/importing markdown alone does not fill memory until Teach / Remember runs.
 */
export async function topicHasUnfiledNotes(path: string | null | undefined): Promise<boolean> {
  if (!path) return false;
  try {
    if (!(await exists(path))) return false;
  } catch {
    return false;
  }
  if ((await countTopicClaims(path)) > 0) return false;
  const notePaths = await collectNotePaths(path);
  return notePaths.some((p) => isRememberableNotePath(p));
}

export async function listProjectSubfolders(path: string): Promise<string[]> {
  if (!(await exists(path))) return [];
  const entries = await readDir(path);
  return filterUserSubfolders(
    entries.filter((e) => e.isDirectory).map((e) => e.name),
  ).sort((a, b) => a.localeCompare(b));
}

export type UpdateProjectOptions = {
  name?: string;
  idea?: string;
  folders?: Array<string | ProjectFolderSpec>;
};

/** Update IDEA.md, add new subfolders, and optionally rename the top-level folder. */
export async function updateProjectFolder(
  path: string,
  opts: UpdateProjectOptions,
): Promise<string> {
  if (!(await exists(path))) throw new Error("Workspace no longer exists");

  if (opts.idea !== undefined) {
    await writeTextFile(`${path}/IDEA.md`, ideaMarkdownFromBody(opts.idea));
  }

  if (opts.folders !== undefined) {
    const entries = await readDir(path);
    const existing = new Set(
      entries.filter((e) => e.isDirectory).map((e) => e.name.toLowerCase()),
    );
    const specs = normalizeFolderSpecs(opts.folders, existing);
    for (const spec of specs) {
      if (existing.has(spec.name.toLowerCase())) continue;
      const dest = `${path}/${spec.name}`;
      if (spec.kind === "import") {
        await copyDirIntoVault(spec.sourcePath, dest);
      } else {
        await mkdir(dest, { recursive: true });
      }
    }
  }

  const currentName = folderNameFromPath(path);
  const nextName = sanitizeFolderName(opts.name ?? currentName);
  if (!nextName) throw new Error("Project name required");
  if (nextName !== currentName) {
    const dest = `${parentDir(path)}/${nextName}`;
    const sameCi = nextName.toLowerCase() === currentName.toLowerCase();
    if (!sameCi && (await exists(dest))) {
      throw new Error(`Project “${nextName}” already exists`);
    }
    await rename(path, dest);
    return dest;
  }
  return path;
}

/** Permanently delete a workspace folder and its contents. */
export async function deleteProjectFolder(path: string): Promise<void> {
  if (!(await exists(path))) return;
  await remove(path, { recursive: true });
}