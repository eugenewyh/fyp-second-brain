export type EditorViewMode = "edit" | "split" | "preview";

const STORAGE_KEY = "second-brain-editor-view";
const SPLIT_KEY = "second-brain-editor-split-ratio";

export const EDITOR_VIEW_DEFAULT: EditorViewMode = "edit";
export const SPLIT_RATIO_DEFAULT = 0.5;

export function loadEditorViewMode(): EditorViewMode {
  if (typeof localStorage === "undefined") return EDITOR_VIEW_DEFAULT;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === "edit" || raw === "split" || raw === "preview") return raw;
  return EDITOR_VIEW_DEFAULT;
}

export function saveEditorViewMode(mode: EditorViewMode): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(STORAGE_KEY, mode);
}

export function loadSplitRatio(): number {
  if (typeof localStorage === "undefined") return SPLIT_RATIO_DEFAULT;
  const raw = localStorage.getItem(SPLIT_KEY);
  const n = raw ? Number(raw) : SPLIT_RATIO_DEFAULT;
  return Number.isFinite(n) && n > 0.2 && n < 0.8 ? n : SPLIT_RATIO_DEFAULT;
}

export function saveSplitRatio(ratio: number): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(SPLIT_KEY, String(ratio));
}