import type { VaultFileRef } from "./flatten";
import { normalizeNoteName, parseWikilinks } from "./wikilinks";

export type NoteBodyReader = (path: string) => Promise<string>;

export interface BacklinkIndex {
  /** normalized target name → paths of notes that link to it */
  byTarget: Map<string, string[]>;
}

export function buildBacklinkIndex(
  files: VaultFileRef[],
  bodies: Record<string, string>,
): BacklinkIndex {
  const byTarget = new Map<string, string[]>();
  const mdFiles = files.filter((f) => f.path.endsWith(".md"));

  for (const file of mdFiles) {
    const body = bodies[file.path];
    if (!body) continue;
    for (const link of parseWikilinks(body)) {
      const key = normalizeNoteName(link.target);
      const existing = byTarget.get(key) ?? [];
      if (!existing.includes(file.path)) {
        byTarget.set(key, [...existing, file.path]);
      }
    }
  }

  return { byTarget };
}

export function backlinksForNote(
  notePath: string | null,
  index: BacklinkIndex,
): string[] {
  if (!notePath) return [];
  const name = notePath.split("/").pop() ?? notePath;
  const key = normalizeNoteName(name);
  return index.byTarget.get(key) ?? [];
}

export function outboundWikilinks(
  notePath: string | null,
  bodies: Record<string, string>,
  files: VaultFileRef[],
): string[] {
  if (!notePath) return [];
  const body = bodies[notePath];
  if (!body) return [];
  const paths: string[] = [];
  for (const link of parseWikilinks(body)) {
    const want = normalizeNoteName(link.target);
    const match = files.find((f) => normalizeNoteName(f.name) === want);
    if (match && !paths.includes(match.path)) paths.push(match.path);
  }
  return paths;
}