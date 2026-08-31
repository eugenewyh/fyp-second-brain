/** Shared model options for the mission bar model picker (Settings-backed). */

/** Default stack on NVIDIA Build NIM (quality → specialty → fallback). */
export const NVIDIA_DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b";
export const NVIDIA_FALLBACK_MODEL = "nvidia/nemotron-3-nano-30b-a3b";

export const NVIDIA_MODELS = [
  "nvidia/nemotron-3-super-120b-a12b", // default
  "openai/gpt-oss-120b", // general / agents
  "deepseek-ai/deepseek-v4-flash-0731", // coding / web-heavy
  "nvidia/nemotron-3-ultra-550b-a55b", // research
  "nvidia/nemotron-3-nano-30b-a3b", // fallback
] as const;

/** Optional BYOK stack on Groq (gpt-oss-20b lives here, not on NVIDIA). */
export const GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b";
export const GROQ_FALLBACK_MODEL = "qwen/qwen3-32b";
export const GROQ_LIGHT_MODEL = "openai/gpt-oss-20b";

export const GROQ_MODELS = [
  "openai/gpt-oss-120b",
  "qwen/qwen3-32b",
  "openai/gpt-oss-20b", // light / Ask-library style
  "meta-llama/llama-4-scout-17b-16e-instruct",
  "llama-3.3-70b-versatile", // legacy / deprecating
] as const;

export const OLLAMA_MODELS = ["qwen3:8b", "llama3.2:3b", "llama3.1:8b"] as const;

export const OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"] as const;

export const XAI_MODELS = ["grok-3", "grok-3-mini", "grok-2"] as const;

/** Optional BYOK OpenRouter presets (IDs change — always include saved LLM_MODEL in UI). */
export const OPENROUTER_MODELS = [
  "nvidia/nemotron-3-ultra-550b-a55b:free",
  "openrouter/free",
  "meta-llama/llama-3.3-70b-instruct:free",
  "qwen/qwen3-coder:free",
  "openai/gpt-4o-mini",
  "anthropic/claude-sonnet-4",
  "google/gemini-2.0-flash-001",
] as const;

export const OPENROUTER_FREE_DEFAULT = "nvidia/nemotron-3-ultra-550b-a55b:free";

export const MODEL_HINTS: Record<string, string> = {
  "nvidia/nemotron-3-super-120b-a12b": "Default · balanced quality",
  "openai/gpt-oss-120b": "General / agents",
  "deepseek-ai/deepseek-v4-flash-0731": "Coding / web-heavy",
  "nvidia/nemotron-3-ultra-550b-a55b": "Research · deepest reasoning",
  "nvidia/nemotron-3-nano-30b-a3b": "Fallback · fast & light",
  "qwen/qwen3-32b": "Fallback if rate-limited · more RPM",
  "openai/gpt-oss-20b": "Light / faster · weaker for deep research",
  "meta-llama/llama-4-scout-17b-16e-instruct": "Fast Scout · medium quality",
  "llama-3.3-70b-versatile": "Legacy · deprecating on Groq",
  "nvidia/nemotron-3-ultra-550b-a55b:free": "Free · strong for agents / research",
  "openrouter/free": "Free · auto-picks a free model",
  "meta-llama/llama-3.3-70b-instruct:free": "Free · general Llama 70B",
  "qwen/qwen3-coder:free": "Free · coding / structured",
};

export type LlmProviderId =
  | "nvidia"
  | "groq"
  | "ollama"
  | "openai"
  | "xai"
  | "openrouter"
  | "openai_compatible";

/** Env var that stores this provider's BYOK secret. */
export type ProviderKeyEnv =
  | "NVIDIA_API_KEY"
  | "GROQ_API_KEY"
  | "XAI_API_KEY"
  | "OPENAI_API_KEY"
  | "OPENROUTER_API_KEY"
  | "LLM_API_KEY"
  | "CUSTOM_API_KEY"
  | null;

export const LLM_PROVIDERS: {
  id: LlmProviderId;
  label: string;
  short: string;
  monogram: string;
  needsKey: boolean;
  needsBaseUrl: boolean;
  showBaseUrl: boolean;
  /** Where the key is persisted in .env */
  keyEnv: ProviderKeyEnv;
  keyPlaceholder?: string;
  defaultBaseUrl?: string;
  defaultModel?: string;
  defaultFallback?: string;
  docsUrl?: string;
  docsLabel?: string;
  hint?: string;
  recommended?: boolean;
  /** Nous ships access — no user connect flow required when server has operator key. */
  bundled?: boolean;
  /** Show optional API key field in config (BYOK override). */
  optionalKey?: boolean;
}[] = [
  {
    id: "nvidia",
    label: "NVIDIA",
    short: "Included with Nous",
    monogram: "NV",
    needsKey: false,
    bundled: true,
    optionalKey: true,
    needsBaseUrl: false,
    showBaseUrl: false,
    keyEnv: "NVIDIA_API_KEY",
    keyPlaceholder: "nvapi-…",
    defaultBaseUrl: "https://integrate.api.nvidia.com/v1",
    defaultModel: NVIDIA_DEFAULT_MODEL,
    defaultFallback: NVIDIA_FALLBACK_MODEL,
    docsUrl: "https://build.nvidia.com/settings/api-keys",
    docsLabel: "Get your own key",
    hint: "No API key needed. Optional: add your own NVIDIA key to use your credits.",
    recommended: true,
  },
  {
    id: "groq",
    label: "Groq",
    short: "Fast cloud · optional BYOK",
    monogram: "Gq",
    needsKey: true,
    needsBaseUrl: false,
    showBaseUrl: false,
    keyEnv: "GROQ_API_KEY",
    keyPlaceholder: "gsk_…",
    defaultModel: GROQ_DEFAULT_MODEL,
    defaultFallback: GROQ_FALLBACK_MODEL,
    docsUrl: "https://console.groq.com/keys",
    docsLabel: "Get API key",
    hint: "Optional. Includes gpt-oss-20b light tier.",
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    short: "Many models · optional BYOK",
    monogram: "OR",
    needsKey: true,
    needsBaseUrl: false,
    showBaseUrl: false,
    keyEnv: "OPENROUTER_API_KEY",
    keyPlaceholder: "sk-or-…",
    defaultBaseUrl: "https://openrouter.ai/api/v1",
    defaultModel: OPENROUTER_FREE_DEFAULT,
    docsUrl: "https://openrouter.ai/models?q=free",
    docsLabel: "Browse free models",
    hint: "Optional. Paste free model ids like nvidia/nemotron-3-ultra-550b-a55b:free",
  },
  {
    id: "xai",
    label: "xAI",
    short: "Official Grok API · optional BYOK",
    monogram: "xAI",
    needsKey: true,
    needsBaseUrl: false,
    showBaseUrl: false,
    keyEnv: "XAI_API_KEY",
    keyPlaceholder: "xai-…",
    defaultBaseUrl: "https://api.x.ai/v1",
    defaultModel: "grok-3-mini",
    defaultFallback: "grok-3",
    docsUrl: "https://console.x.ai",
    docsLabel: "console.x.ai",
    hint: "Optional. Grok models via your xAI key.",
  },
  {
    id: "openai",
    label: "OpenAI",
    short: "GPT models · optional BYOK",
    monogram: "OA",
    needsKey: true,
    needsBaseUrl: false,
    showBaseUrl: false,
    keyEnv: "OPENAI_API_KEY",
    keyPlaceholder: "sk-…",
    defaultBaseUrl: "https://api.openai.com/v1",
    defaultModel: "gpt-4o-mini",
    defaultFallback: "gpt-4o-mini",
    docsUrl: "https://platform.openai.com/api-keys",
    docsLabel: "API keys",
  },
  {
    id: "ollama",
    label: "Ollama",
    short: "Fully local · no key",
    monogram: "Ol",
    needsKey: false,
    needsBaseUrl: false,
    showBaseUrl: false,
    keyEnv: null,
    defaultModel: "qwen3:8b",
    hint: "Local models. Embeddings also use Ollama.",
  },
  {
    id: "openai_compatible",
    label: "Custom endpoint",
    short: "OpenAI-compatible URL",
    monogram: "API",
    needsKey: true,
    needsBaseUrl: true,
    showBaseUrl: true,
    keyEnv: "CUSTOM_API_KEY",
    keyPlaceholder: "API key",
    defaultModel: "gpt-4o-mini",
    hint: "Any gateway that speaks the OpenAI chat API.",
  },
];

export function keyEnvForProvider(id: string): ProviderKeyEnv {
  return providerMeta(id).keyEnv;
}

/** Whether env values indicate this provider is connected. */
export function isProviderConnected(
  id: string,
  values: Record<string, string>,
  opts?: {
    connected?: Record<string, boolean> | null;
    /** Sidecar reports Nous-included NVIDIA access (no user key). */
    llmBundled?: boolean;
  },
): boolean {
  const m = providerMeta(id);
  // Shipped with Nous — always in Connected; optional BYOK via Config only.
  if (m.bundled) {
    return true;
  }
  if (opts?.connected && id in opts.connected) {
    return !!opts.connected[id];
  }
  if (!m.needsKey) return true; // ollama
  if (id === "openai_compatible") {
    const key = values.CUSTOM_API_KEY?.trim() || values.LLM_API_KEY?.trim();
    const base = values.CUSTOM_BASE_URL?.trim() || values.LLM_BASE_URL?.trim();
    return !!(key && base);
  }
  if (m.keyEnv && values[m.keyEnv]?.trim()) return true;
  // Legacy: active provider with only LLM_API_KEY set
  if (values.LLM_PROVIDER === id && values.LLM_API_KEY?.trim()) return true;
  return false;
}

export function modelsForProvider(provider: string, currentModel?: string | null): string[] {
  let base: string[];
  switch (provider) {
    case "nvidia":
      base = [...NVIDIA_MODELS];
      break;
    case "ollama":
      base = [...OLLAMA_MODELS];
      break;
    case "openai":
      base = [...OPENAI_MODELS];
      break;
    case "xai":
      base = [...XAI_MODELS];
      break;
    case "openrouter":
      base = [...OPENROUTER_MODELS];
      break;
    case "openai_compatible":
      base = [...OPENAI_MODELS, ...XAI_MODELS];
      break;
    case "groq":
      base = [...GROQ_MODELS];
      break;
    default:
      base = [...NVIDIA_MODELS];
  }
  const cur = currentModel?.trim();
  // Always surface the saved/settings model even if it's a custom free id
  if (cur && !base.includes(cur)) {
    return [cur, ...base];
  }
  return base;
}

export function providerMeta(id: string) {
  return LLM_PROVIDERS.find((p) => p.id === id) ?? LLM_PROVIDERS[0];
}

/**
 * When switching provider, keep a valid current model when possible.
 * OpenRouter / custom / ollama allow free-form ids (e.g. *:free).
 */
export function resolveModelForProvider(provider: string, current: string | undefined): string {
  const meta = providerMeta(provider);
  const cur = current?.trim() ?? "";
  const list = modelsForProvider(provider);

  if (cur) {
    if (list.includes(cur)) return cur;
    // Freeform IDs: never clobber user's OpenRouter free model
    if (
      provider === "openrouter" ||
      provider === "openai_compatible" ||
      provider === "ollama"
    ) {
      return cur;
    }
  }
  return meta.defaultModel ?? list[0] ?? cur ?? "";
}

export function shortModelLabel(model: string): string {
  if (!model) return "Model";
  // Keep :free visible so users know it's the free endpoint
  const free = model.endsWith(":free") ? " (free)" : "";
  let base = model.includes("/") ? model.split("/").pop()! : model;
  base = base.replace(/:free$/, "");
  const label = base.length > 20 ? `${base.slice(0, 18)}…` : base;
  return `${label}${free}`;
}

/** Display name without the free suffix (badge used instead in pickers). */
export function modelDisplayName(model: string): string {
  if (!model) return "Model";
  let base = model.includes("/") ? model.split("/").pop()! : model;
  base = base.replace(/:free$/i, "");
  return base.length > 28 ? `${base.slice(0, 26)}…` : base;
}

export type ModelPickerGroup = {
  providerId: LlmProviderId;
  label: string;
  models: string[];
};

/** Providers + models for the composer picker (searchable, grouped). */
export function modelPickerGroups(
  currentProvider: string,
  currentModel?: string | null,
  opts?: { connected?: Record<string, boolean> | null; query?: string },
): ModelPickerGroup[] {
  const q = (opts?.query ?? "").trim().toLowerCase();
  const groups: ModelPickerGroup[] = [];

  for (const p of LLM_PROVIDERS) {
    if (p.id === "openai_compatible") continue;
    const models = modelsForProvider(
      p.id,
      p.id === currentProvider ? currentModel : null,
    );
    const filtered = q
      ? models.filter(
          (m) =>
            m.toLowerCase().includes(q) ||
            modelDisplayName(m).toLowerCase().includes(q) ||
            p.label.toLowerCase().includes(q),
        )
      : models;
    if (!filtered.length) continue;
    groups.push({ providerId: p.id, label: p.label, models: filtered });
  }

  return groups;
}

export function modelHint(model: string): string {
  return MODEL_HINTS[model] ?? (model.includes(":free") ? "Free on OpenRouter" : "");
}

export function isFreeModel(model: string): boolean {
  if (/:free$/i.test(model)) return true;
  const hint = modelHint(model).toLowerCase();
  return hint.startsWith("free");
}
