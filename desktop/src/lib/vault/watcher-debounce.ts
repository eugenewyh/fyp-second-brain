export type DebouncedFn = (path: string) => void;

export function createDebouncedHandler(
  fn: DebouncedFn,
  delayMs = 2000,
): { schedule: DebouncedFn; cancelAll: () => void } {
  const timers = new Map<string, ReturnType<typeof setTimeout>>();

  function schedule(path: string) {
    const existing = timers.get(path);
    if (existing) clearTimeout(existing);
    timers.set(
      path,
      setTimeout(() => {
        timers.delete(path);
        fn(path);
      }, delayMs),
    );
  }

  function cancelAll() {
    for (const timer of timers.values()) clearTimeout(timer);
    timers.clear();
  }

  return { schedule, cancelAll };
}