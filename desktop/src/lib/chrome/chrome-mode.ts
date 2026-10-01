export type ChromeMode = "solid" | "idle-glass";

export type ChromeModeContext = {
  isHome: boolean;
  sessionIdle: boolean;
};

export const CHROME_MODE_CHANGE_EVENT = "nous-chrome-mode-change";

export function resolveChromeMode(ctx: ChromeModeContext): ChromeMode {
  return ctx.isHome && ctx.sessionIdle ? "idle-glass" : "solid";
}

export function applyChromeMode(mode: ChromeMode): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  const current = root.dataset.chromeMode === "idle-glass" ? "idle-glass" : "solid";
  if (current === mode) return;

  if (mode === "idle-glass") {
    root.dataset.chromeMode = "idle-glass";
  } else {
    delete root.dataset.chromeMode;
  }

  window.dispatchEvent(
    new CustomEvent(CHROME_MODE_CHANGE_EVENT, { detail: { mode } }),
  );
}

export function syncChromeMode(ctx: ChromeModeContext): ChromeMode {
  const mode = resolveChromeMode(ctx);
  applyChromeMode(mode);
  return mode;
}
