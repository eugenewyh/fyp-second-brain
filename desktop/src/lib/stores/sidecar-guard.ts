/** How long /health must stay down before one automatic sidecar restart. */
export const SIDECAR_RESTART_AFTER_MS = 20_000;
/** Minimum gap between automatic restarts so a cold boot is not killed twice. */
export const SIDECAR_RESTART_COOLDOWN_MS = 30_000;
/** Cheap /health ping while the sidecar is up. */
export const SIDECAR_KEEPALIVE_MS = 2_000;
/** Recheck delay after a single missed keepalive, before flipping offline. */
export const SIDECAR_CONFIRM_MS = 80;
/** Misses required before a live session is marked offline. */
export const SIDECAR_KEEPALIVE_MISSES = 2;

const FAST_PROBE_MS = 50;
const MID_PROBE_MS = 150;
const SLOW_PROBE_MS = 400;
const IDLE_PROBE_MS = 1_000;

export type GuardTick = {
  online: boolean;
  becameOnline: boolean;
  becameOffline: boolean;
  restarted: boolean;
  nextDelayMs: number;
  message: string;
};

/** Poll fastest while the process is likely still binding the port. */
export function nextOfflineProbeDelayMs(downForMs: number): number {
  if (downForMs < 800) return FAST_PROBE_MS;
  if (downForMs < 4_000) return MID_PROBE_MS;
  if (downForMs < SIDECAR_RESTART_AFTER_MS) return SLOW_PROBE_MS;
  return IDLE_PROBE_MS;
}

/** Gaps between explicit waitForSidecar attempts. Caps quickly; success returns immediately. */
export function sidecarProbeDelayMs(failedAttempts: number): number {
  const steps = [40, 80, 120, 180, 250];
  const i = Math.min(Math.max(failedAttempts, 0), steps.length - 1);
  return steps[i] ?? 250;
}

export function shouldAutoRestartSidecar(opts: {
  downForMs: number;
  lastRestartAt: number;
  now: number;
}): boolean {
  if (opts.downForMs < SIDECAR_RESTART_AFTER_MS) return false;
  if (opts.lastRestartAt !== 0 && opts.now - opts.lastRestartAt < SIDECAR_RESTART_COOLDOWN_MS) {
    return false;
  }
  return true;
}

/**
 * Keeps a local sidecar session alive.
 * Health success is the online signal. A restart happens only after a long outage,
 * and never on the first few seconds of boot.
 */
export class SidecarGuard {
  online = false;
  downSince = 0;
  lastRestartAt = 0;
  misses = 0;

  constructor(
    private readonly probe: () => Promise<boolean>,
    private readonly restart: () => Promise<void>,
    private readonly now: () => number = Date.now,
  ) {}

  forceOnline() {
    this.online = true;
    this.downSince = 0;
    this.misses = 0;
  }

  forceOffline() {
    this.online = false;
    this.misses = 0;
    if (this.downSince === 0) this.downSince = this.now();
  }

  noteRestart(at = this.now()) {
    this.lastRestartAt = at;
    this.downSince = at;
    this.online = false;
    this.misses = 0;
  }

  async tick(): Promise<GuardTick> {
    const up = await this.probe();
    const t = this.now();
    if (up) {
      const becameOnline = !this.online;
      this.forceOnline();
      return {
        online: true,
        becameOnline,
        becameOffline: false,
        restarted: false,
        nextDelayMs: SIDECAR_KEEPALIVE_MS,
        message: "",
      };
    }

    this.misses += 1;
    if (this.online && this.misses < SIDECAR_KEEPALIVE_MISSES) {
      return {
        online: true,
        becameOnline: false,
        becameOffline: false,
        restarted: false,
        nextDelayMs: SIDECAR_CONFIRM_MS,
        message: "",
      };
    }

    const becameOffline = this.online;
    this.online = false;
    if (this.downSince === 0) this.downSince = t;
    const downFor = t - this.downSince;
    let restarted = false;
    if (
      shouldAutoRestartSidecar({
        downForMs: downFor,
        lastRestartAt: this.lastRestartAt,
        now: t,
      })
    ) {
      this.noteRestart(t);
      restarted = true;
      try {
        await this.restart();
      } catch {
        /* still down — the next probes keep going */
      }
    }
    const stillDownFor = t - this.downSince;
    return {
      online: false,
      becameOnline: false,
      becameOffline,
      restarted,
      nextDelayMs: nextOfflineProbeDelayMs(stillDownFor),
      message:
        downFor < 1_500
          ? ""
          : "Can't reach the AI sidecar on port 8765. Retrying…",
    };
  }
}
