import { invoke } from "@tauri-apps/api/core";
import { readDir, readTextFile, writeTextFile, exists, mkdir } from "@tauri-apps/plugin-fs";
import type { VaultNode } from "./types";

const SUPPORTED_EXTENSIONS = new Set([".md", ".txt", ".pdf"]);

export async function getProjectRoot(): Promise<string> {
  return invoke<string>("get_project_root");
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