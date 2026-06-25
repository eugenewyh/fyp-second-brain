import type { ResearchResult } from "$lib/api";
import { getVaultRoot, writeNote } from "./load";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

export function buildResearchNoteContent(result: ResearchResult): string {
  const date = new Date().toISOString().slice(0, 10);
  const tags = ["research", "auto-generated"];
  const sources = Object.keys(result.retrieval_stats ?? {}).join(", ");
  const frontmatter = [
    "---",
    `date: ${date}`,
    `query: "${result.query.replace(/"/g, '\\"')}"`,
    `sources: "${sources}"`,
    `tags: [${tags.map((t) => `"${t}"`).join(", ")}]`,
    `confidence: ${result.revision_count}`,
    `revisions: ${result.revision_count}`,
    "---",
    "",
  ].join("\n");
  return `${frontmatter}# ${result.query}\n\n${result.report}\n`;
}

export async function saveResearchAsNote(result: ResearchResult): Promise<string> {
  const vaultRoot = await getVaultRoot();
  const date = new Date().toISOString().slice(0, 10);
  const slug = slugify(result.query) || "research";
  const path = `${vaultRoot}/research/${slug}-${date}.md`;
  await writeNote(path, buildResearchNoteContent(result));
  return path;
}