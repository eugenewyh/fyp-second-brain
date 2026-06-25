import { describe, expect, it, vi } from "vitest";
import { createDebouncedHandler } from "./watcher-debounce";

describe("watcher-debounce", () => {
  it("debounces calls per path", async () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const { schedule } = createDebouncedHandler(fn, 1000);

    schedule("/a.md");
    schedule("/a.md");
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith("/a.md");
    vi.useRealTimers();
  });
});