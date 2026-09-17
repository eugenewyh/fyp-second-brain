import { describe, expect, it } from "vitest";
import { parseLocalEngine } from "./local-engine";
import {
  disconnectChoose,
  isProviderConnected,
  LLM_PROVIDERS,
  modelPickerGroups,
  modelsForProvider,
  resolveModelForProvider,
} from "./models";

const STUB_MODEL = {
  id: "stub/tiny-moe",
  display_name: "Stub Tiny MoE",
  disk_bytes: 1024,
  context_window: 2048,
  active_params_b: 0.1,
  total_params_b: 1.0,
};

describe("parseLocalEngine", () => {
  it("parses ready JSON without copying endpoint fields", () => {
    const parsed = parseLocalEngine({
      kind: "ready",
      model: STUB_MODEL,
      started_at: 1710000000,
      base_url: "http://127.0.0.1:9",
      token: "secret",
      pid: 4242,
    });
    expect(parsed).toEqual({
      kind: "ready",
      model: STUB_MODEL,
      started_at: 1710000000,
    });
    const raw = JSON.stringify(parsed);
    expect(raw).not.toContain("base_url");
    expect(raw).not.toContain("token");
    expect(raw).not.toContain("pid");
    expect(raw).not.toContain("secret");
  });
});

describe("isProviderConnected local", () => {
  it("is false without connected.local, even though the catalog row has no key", () => {
    expect(isProviderConnected("local", {})).toBe(false);
    expect(isProviderConnected("local", {}, { connected: { nvidia: true } })).toBe(false);
    expect(isProviderConnected("local", {}, { connected: { local: false } })).toBe(false);
  });

  it("is true only when connected.local is true", () => {
    expect(isProviderConnected("local", {}, { connected: { local: true } })).toBe(true);
  });
});

describe("resolveModelForProvider local", () => {
  it("keeps a freeform local model id", () => {
    expect(resolveModelForProvider("local", "stub/tiny-moe")).toBe("stub/tiny-moe");
  });
});

describe("modelsForProvider local", () => {
  it("returns empty unless a current model id is set", () => {
    expect(modelsForProvider("local")).toEqual([]);
    expect(modelsForProvider("local", "stub/tiny-moe")).toEqual(["stub/tiny-moe"]);
  });
});

describe("modelPickerGroups local", () => {
  it("shows an On-device group when the current provider is local", () => {
    const groups = modelPickerGroups("local", "stub/tiny-moe");
    expect(groups.some((g) => g.providerId === "local" && g.models.includes("stub/tiny-moe"))).toBe(
      true,
    );
  });

  it("shows an On-device group when the ready model id is the current model", () => {
    const groups = modelPickerGroups("local", STUB_MODEL.id);
    const local = groups.find((g) => g.providerId === "local");
    expect(local?.models).toEqual([STUB_MODEL.id]);
  });
});

describe("disconnectChoose", () => {
  it("picks bundled NVIDIA first even if local is ready", () => {
    expect(disconnectChoose(LLM_PROVIDERS, {}, "ready")).toBe("nvidia");
    expect(
      disconnectChoose(LLM_PROVIDERS, { GROQ_API_KEY: "gsk_x" }, "ready"),
    ).toBe("nvidia");
  });

  it("picks NVIDIA when an NVIDIA key remains and NVIDIA is not bundled", () => {
    expect(
      disconnectChoose(
        [
          { id: "nvidia", keyEnv: "NVIDIA_API_KEY", bundled: false },
          { id: "local", keyEnv: null },
        ],
        { NVIDIA_API_KEY: "nvapi-x" },
        "ready",
      ),
    ).toBe("nvidia");
  });

  it("picks the first stored BYOK key when NVIDIA is neither bundled nor keyed", () => {
    expect(
      disconnectChoose(
        [
          { id: "nvidia", keyEnv: "NVIDIA_API_KEY", bundled: false },
          { id: "groq", keyEnv: "GROQ_API_KEY" },
          { id: "openai", keyEnv: "OPENAI_API_KEY" },
          { id: "local", keyEnv: null },
          { id: "ollama", keyEnv: null },
        ],
        { OPENAI_API_KEY: "sk-x" },
        "ready",
      ),
    ).toBe("openai");
  });

  it("picks local when ready after NVIDIA and other keys are gone", () => {
    expect(
      disconnectChoose(
        [
          { id: "nvidia", keyEnv: "NVIDIA_API_KEY", bundled: false },
          { id: "groq", keyEnv: "GROQ_API_KEY" },
          { id: "ollama", keyEnv: null },
          { id: "local", keyEnv: null },
        ],
        {},
        "ready",
      ),
    ).toBe("local");
  });

  it("does not fall back to ollama when local is not ready", () => {
    expect(
      disconnectChoose(
        [
          { id: "nvidia", keyEnv: "NVIDIA_API_KEY", bundled: false },
          { id: "ollama", keyEnv: null },
          { id: "local", keyEnv: null },
        ],
        {},
        "not_installed",
      ),
    ).toBe("nvidia");
  });
});
