import { describe, expect, it } from "vitest";
import {
  SIDECAR_CONFIRM_MS,
  SIDECAR_KEEPALIVE_MS,
  SIDECAR_RESTART_AFTER_MS,
  SidecarGuard,
  nextOfflineProbeDelayMs,
  shouldAutoRestartSidecar,
  sidecarProbeDelayMs,
} from "./sidecar-guard";

describe("nextOfflineProbeDelayMs", () => {
  it("polls immediately while the sidecar is still starting", () => {
    expect(nextOfflineProbeDelayMs(0)).toBe(50);
    expect(nextOfflineProbeDelayMs(799)).toBe(50);
    expect(nextOfflineProbeDelayMs(800)).toBe(150);
    expect(nextOfflineProbeDelayMs(SIDECAR_RESTART_AFTER_MS)).toBe(1000);
  });
});

describe("sidecarProbeDelayMs", () => {
  it("backs off a little and then stays short", () => {
    expect(sidecarProbeDelayMs(0)).toBe(40);
    expect(sidecarProbeDelayMs(4)).toBe(250);
    expect(sidecarProbeDelayMs(40)).toBe(250);
  });
});

describe("shouldAutoRestartSidecar", () => {
  it("leaves a booting process alone", () => {
    expect(
      shouldAutoRestartSidecar({ downForMs: 19_999, lastRestartAt: 0, now: 50_000 }),
    ).toBe(false);
  });

  it("restarts after a long outage", () => {
    expect(
      shouldAutoRestartSidecar({ downForMs: 20_000, lastRestartAt: 0, now: 50_000 }),
    ).toBe(true);
  });

  it("waits out the cooldown so a cold start is not killed twice", () => {
    expect(
      shouldAutoRestartSidecar({ downForMs: 20_000, lastRestartAt: 40_000, now: 50_000 }),
    ).toBe(false);
    expect(
      shouldAutoRestartSidecar({ downForMs: 20_000, lastRestartAt: 10_000, now: 50_000 }),
    ).toBe(true);
  });
});

describe("SidecarGuard", () => {
  it("comes online on the first healthy probe", async () => {
    const guard = new SidecarGuard(async () => true, async () => {});
    const tick = await guard.tick();
    expect(tick.becameOnline).toBe(true);
    expect(tick.online).toBe(true);
    expect(tick.restarted).toBe(false);
    expect(tick.nextDelayMs).toBe(SIDECAR_KEEPALIVE_MS);
  });

  it("ignores one missed keepalive", async () => {
    let up = true;
    const guard = new SidecarGuard(async () => up, async () => {});
    await guard.tick();
    up = false;
    const miss = await guard.tick();
    expect(miss.online).toBe(true);
    expect(miss.becameOffline).toBe(false);
    expect(miss.nextDelayMs).toBe(SIDECAR_CONFIRM_MS);
  });

  it("marks offline after a second miss and recovers on the next success", async () => {
    let up = true;
    const guard = new SidecarGuard(async () => up, async () => {});
    await guard.tick();
    up = false;
    await guard.tick();
    const down = await guard.tick();
    expect(down.online).toBe(false);
    expect(down.becameOffline).toBe(true);
    up = true;
    const back = await guard.tick();
    expect(back.becameOnline).toBe(true);
    expect(back.online).toBe(true);
  });

  it("does not restart during boot, then restarts once", async () => {
    let now = 1_000;
    const restarts: number[] = [];
    const guard = new SidecarGuard(
      async () => false,
      async () => {
        restarts.push(now);
      },
      () => now,
    );
    await guard.tick();
    expect(restarts).toEqual([]);
    now = 1_000 + SIDECAR_RESTART_AFTER_MS;
    const tick = await guard.tick();
    expect(tick.restarted).toBe(true);
    expect(restarts).toEqual([now]);
    const again = await guard.tick();
    expect(again.restarted).toBe(false);
    expect(restarts).toEqual([now]);
  });
});
