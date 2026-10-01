import { afterEach, describe, expect, it, vi } from "vitest";
import {
  applyChromeMode,
  CHROME_MODE_CHANGE_EVENT,
  resolveChromeMode,
  syncChromeMode,
} from "./chrome-mode";

describe("resolveChromeMode", () => {
  it("is idle-glass only when home and session are idle", () => {
    expect(resolveChromeMode({ isHome: true, sessionIdle: true })).toBe(
      "idle-glass",
    );
    expect(resolveChromeMode({ isHome: true, sessionIdle: false })).toBe(
      "solid",
    );
    expect(resolveChromeMode({ isHome: false, sessionIdle: true })).toBe(
      "solid",
    );
    expect(resolveChromeMode({ isHome: false, sessionIdle: false })).toBe(
      "solid",
    );
  });
});

describe("applyChromeMode", () => {
  afterEach(() => {
    delete document.documentElement.dataset.chromeMode;
    vi.restoreAllMocks();
  });

  it("sets data-chrome-mode for idle-glass and removes it for solid", () => {
    applyChromeMode("idle-glass");
    expect(document.documentElement.dataset.chromeMode).toBe("idle-glass");

    applyChromeMode("solid");
    expect(document.documentElement.dataset.chromeMode).toBeUndefined();
  });

  it("is idempotent and only dispatches on change", () => {
    const spy = vi.fn();
    window.addEventListener(CHROME_MODE_CHANGE_EVENT, spy);

    applyChromeMode("idle-glass");
    applyChromeMode("idle-glass");
    applyChromeMode("solid");
    applyChromeMode("solid");

    expect(spy).toHaveBeenCalledTimes(2);
    window.removeEventListener(CHROME_MODE_CHANGE_EVENT, spy);
  });
});

describe("syncChromeMode", () => {
  afterEach(() => {
    delete document.documentElement.dataset.chromeMode;
  });

  it("resolves and applies in one call", () => {
    expect(syncChromeMode({ isHome: true, sessionIdle: true })).toBe(
      "idle-glass",
    );
    expect(document.documentElement.dataset.chromeMode).toBe("idle-glass");

    expect(syncChromeMode({ isHome: false, sessionIdle: true })).toBe("solid");
    expect(document.documentElement.dataset.chromeMode).toBeUndefined();
  });
});
