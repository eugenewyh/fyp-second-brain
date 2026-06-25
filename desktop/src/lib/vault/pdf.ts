import { readFile } from "@tauri-apps/plugin-fs";

export async function readPdfBytes(path: string): Promise<Uint8Array> {
  return readFile(path);
}

export function isPdfPath(path: string): boolean {
  return path.toLowerCase().endsWith(".pdf");
}