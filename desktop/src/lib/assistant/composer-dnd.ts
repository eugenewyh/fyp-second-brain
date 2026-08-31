/**
 * Finder / OS file drops for the composer.
 *
 * Tauri intercepts native file drags, so HTML5 `ondrop` alone often never
 * receives real paths. Use `getCurrentWebview().onDragDropEvent` instead.
 *
 * Drops of .md / .txt / .pdf / .docx always stage into the active composer — position
 * hit-testing is only used for the drag-over highlight.
 */
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { getCurrentWindow } from "@tauri-apps/api/window";

export type ComposerDropTarget = {
  setDragOver: (over: boolean) => void;
  containsPoint: (clientX: number, clientY: number) => boolean;
  stagePaths: (paths: string[]) => void;
};

const ATTACH_EXT = /\.(md|txt|pdf|docx)$/i;

const targets = new Set<ComposerDropTarget>();
let unlisten: (() => void) | null = null;
let starting: Promise<void> | null = null;
let lastOver: ComposerDropTarget | null = null;

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function isAttachablePath(path: string): boolean {
  const cleaned = path.replace(/^file:\/\//i, "");
  const name = cleaned.split(/[\\/]/).pop() ?? cleaned;
  return ATTACH_EXT.test(name);
}

export function filterAttachablePaths(paths: string[]): string[] {
  return paths
    .map((p) => p.replace(/^file:\/\//i, ""))
    .filter(isAttachablePath);
}

function clearHighlights() {
  for (const t of targets) t.setDragOver(false);
  lastOver = null;
}

function targetAt(clientX: number, clientY: number): ComposerDropTarget | null {
  for (const t of targets) {
    if (t.containsPoint(clientX, clientY)) return t;
  }
  return null;
}

function logicalPoint(position: {
  x: number;
  y: number;
  toLogical?: (factor: number) => { x: number; y: number };
}, scaleFactor: number): { x: number; y: number } {
  if (typeof position.toLogical === "function") {
    return position.toLogical(scaleFactor);
  }
  return { x: position.x / scaleFactor, y: position.y / scaleFactor };
}

async function ensureListening(): Promise<void> {
  if (!isTauri() || unlisten || starting) return starting ?? undefined;
  starting = (async () => {
    try {
      const webview = getCurrentWebview();
      const win = getCurrentWindow();
      unlisten = await webview.onDragDropEvent(async (event) => {
        const payload = event.payload;
        if (payload.type === "leave") {
          clearHighlights();
          return;
        }

        let scale = 1;
        try {
          scale = await win.scaleFactor();
        } catch {
          scale =
            typeof window !== "undefined" && window.devicePixelRatio
              ? window.devicePixelRatio
              : 1;
        }

        const { x, y } = logicalPoint(
          payload.position as {
            x: number;
            y: number;
            toLogical?: (factor: number) => { x: number; y: number };
          },
          scale,
        );
        const hit = targetAt(x, y);

        if (payload.type === "enter" || payload.type === "over") {
          clearHighlights();
          // Highlight any registered composer while files are dragged in-window.
          // Prefer the hit target; otherwise light up the first (visible) one.
          const highlight = hit ?? [...targets][0] ?? null;
          if (highlight) {
            highlight.setDragOver(true);
            lastOver = highlight;
          }
          return;
        }

        if (payload.type === "drop") {
          const paths = filterAttachablePaths(payload.paths ?? []);
          const target = hit ?? lastOver ?? [...targets][0] ?? null;
          clearHighlights();
          // Always stage attachable Finder drops — do not require pixel-perfect hit.
          if (paths.length && target) {
            target.stagePaths(paths);
          }
        }
      });
    } catch (err) {
      console.warn("[composer-dnd] Failed to bind Tauri drag-drop:", err);
      unlisten = null;
    } finally {
      starting = null;
    }
  })();
  return starting;
}

/** Register a composer drop surface. Returns unregister. */
export function registerComposerDropTarget(target: ComposerDropTarget): () => void {
  targets.add(target);
  void ensureListening();
  return () => {
    targets.delete(target);
    target.setDragOver(false);
    if (lastOver === target) lastOver = null;
    if (targets.size === 0 && unlisten) {
      unlisten();
      unlisten = null;
    }
  };
}
