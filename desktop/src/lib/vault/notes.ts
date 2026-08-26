import type { ResearchResult } from "$lib/api";
import { api } from "$lib/api";
import { getVaultRoot, writeNote } from "./load";
import { workspace } from "$lib/stores/workspace.svelte";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

export function buildResearchNoteContent(
  result: ResearchResult,
  opts?: { projectPath?: string | null },
): string {
  const date = new Date().toISOString().slice(0, 10);
  const tags = ["research", "auto-generated"];
  const sources = Object.keys(result.retrieval_stats ?? {}).join(", ");
  const project =
    opts?.projectPath?.split(/[\\/]/).filter(Boolean).pop() ??
    (opts?.projectPath ? opts.projectPath : "");
  const frontmatter = [
    "---",
    `date: ${date}`,
    `query: "${result.query.replace(/"/g, '\\"')}"`,
    `sources: "${sources}"`,
    `tags: [${tags.map((t) => `"${t}"`).join(", ")}]`,
    `revisions: ${result.revision_count}`,
    "type: research-report",
    project ? `project: "${project.replace(/"/g, '\\"')}"` : null,
    opts?.projectPath
      ? `project_path: "${String(opts.projectPath).replace(/"/g, '\\"')}"`
      : null,
    "---",
    "",
  ]
    .filter(Boolean)
    .join("\n");
  return `${frontmatter}# ${result.query}\n\n${result.report}\n`;
}

/** Prefer project-local research folder when a project path is set. */
export async function researchNoteDir(projectPath?: string | null): Promise<string> {
  const vaultRoot = await getVaultRoot();
  if (projectPath && projectPath.trim()) {
    // projectPath is already a folder under the vault
    return `${projectPath.replace(/\/$/, "")}/research`;
  }
  return `${vaultRoot}/research`;
}

export async function saveResearchAsNote(
  result: ResearchResult,
  opts?: { projectPath?: string | null },
): Promise<string> {
  const projectPath =
    opts?.projectPath !== undefined ? opts.projectPath : workspace.activeTopicPath;
  const dir = await researchNoteDir(projectPath);
  const date = new Date().toISOString().slice(0, 10);
  const time = new Date().toISOString().slice(11, 19).replace(/:/g, "");
  const slug = slugify(result.query) || "research";
  const path = `${dir}/${date}-${time}-${slug}.md`;
  await writeNote(path, buildResearchNoteContent(result, { projectPath }));
  return path;
}

/** Off-topic lookups stay in the thread; do not write them into the topic vault. */
export function shouldSaveResearchToVault(
  result: Pick<ResearchResult, "memory_written">,
): boolean {
  return result.memory_written !== false;
}

/** Save report to vault and re-index into Chroma so future research can use it. */
export async function saveAndIndexResearch(
  result: ResearchResult,
  opts?: { projectPath?: string | null },
): Promise<{ path: string; indexed: boolean }> {
  const path = await saveResearchAsNote(result, opts);
  let indexed = false;
  try {
    await api.ingestFile(path);
    indexed = true;
  } catch {
    /* file saved even if index fails (e.g. embeddings offline) */
  }
  return { path, indexed };
}
