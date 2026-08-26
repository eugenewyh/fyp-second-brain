import { invoke } from "@tauri-apps/api/core";
import { readDir, readFile } from "@tauri-apps/plugin-fs";
import { flattenVaultFiles } from "./flatten";
import { loadVaultTree } from "./load";

async function getProjectRoot(): Promise<string> {
  return invoke<string>("get_project_root");
}

async function getVaultRoot(): Promise<string> {
  const root = await getProjectRoot();
  return `${root}/data/documents`;
}

async function findByBasenameRecursive(dir: string, basename: string): Promise<string | null> {
  try {
    const entries = await readDir(dir);
    for (const e of entries) {
      const full = `${dir}/${e.name}`;
      if (e.isDirectory) {
        const hit = await findByBasenameRecursive(full, basename);
        if (hit) return hit;
      } else if (e.name.toLowerCase() === basename.toLowerCase()) {
        return full;
      }
    }
  } catch {}
  return null;
}

export async function readPdfBytes(inputPath: string): Promise<Uint8Array> {
  let path = inputPath.trim();

  // Step 1: If it looks like a concrete path, try direct fs read first (fast path)
  if (path.includes("/") || path.includes("\\") || path.startsWith("~")) {
    try {
      return await readFile(path);
    } catch {
      // continue to name resolution
    }
  }

  const basename = path.split(/[\\/]/).pop() || path;

  // Step 2: Search the vault tree from JS side (very reliable)
  try {
    const root = await getVaultRoot();
    const found = await findByBasenameRecursive(root, basename);
    if (found) {
      return await readFile(found);
    }
  } catch (e) {
    // ignore and try rust
  }

  // Step 3: Ask Rust via base64 (avoids huge number[] JSON for large PDFs)
  try {
    const b64 = await invoke<string>("read_vault_file_base64", { path: basename });
    const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    if (bin.length < 4) throw new Error("base64 decode produced empty data");
    return bin;
  } catch (rustErr: any) {
    // Last attempt with original input
    try {
      const b64 = await invoke<string>("read_vault_file_base64", { path });
      const bin = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      if (bin.length < 4) throw new Error("base64 decode produced empty data");
      return bin;
    } catch (rustErr2: any) {
      const m1 = rustErr?.message || String(rustErr);
      const m2 = rustErr2?.message || String(rustErr2);
      throw new Error(`Could not read PDF "${path}" (basename=${basename}).\nRust1: ${m1}\nRust2: ${m2}`);
    }
  }
}

export function isPdfPath(path: string): boolean {
  return path.toLowerCase().endsWith(".pdf");
}

/** Upgrade a bare filename (e.g. from recents) to a full vault path when possible. */
export async function resolveBarePdf(inputPath: string): Promise<string> {
  const path = inputPath.trim();
  if (!path || path.includes("/") || path.includes("\\")) return path;
  if (!isPdfPath(path)) return path;

  try {
    const root = await getVaultRoot();
    const tree = await loadVaultTree(root);
    const files = flattenVaultFiles(tree);
    const hit = files.find((f) => f.name.toLowerCase() === path.toLowerCase());
    if (hit) return hit.path;
  } catch {
    // fall through — readPdfBytes has additional resolution strategies
  }
  return path;
}
