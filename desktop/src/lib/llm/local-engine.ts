export type LocalModelCard = {
  id: string;
  display_name: string;
  disk_bytes: number;
  context_window: number;
  active_params_b: number;
  total_params_b: number;
};

export type LocalEngine =
  | { kind: "unsupported"; reason: string; detail: string }
  | { kind: "not_installed"; model: LocalModelCard; download_bytes: number }
  | {
      kind: "acquiring";
      model: LocalModelCard;
      step: string;
      done_bytes: number;
      total_bytes: number;
      eta_s: number | null;
    }
  | { kind: "starting"; model: LocalModelCard; elapsed_s: number }
  | { kind: "ready"; model: LocalModelCard; started_at: number }
  | { kind: "failed"; stage: string; message: string; retryable: boolean };

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value == null || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function str(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function bool(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function parseModelCard(raw: unknown): LocalModelCard | null {
  const o = asRecord(raw);
  if (!o) return null;
  const id = str(o.id);
  const display_name = str(o.display_name);
  const disk_bytes = num(o.disk_bytes);
  const context_window = num(o.context_window);
  const active_params_b = num(o.active_params_b);
  const total_params_b = num(o.total_params_b);
  if (
    id == null ||
    display_name == null ||
    disk_bytes == null ||
    context_window == null ||
    active_params_b == null ||
    total_params_b == null
  ) {
    return null;
  }
  return { id, display_name, disk_bytes, context_window, active_params_b, total_params_b };
}

function parseEta(value: unknown): number | null | undefined {
  if (value == null) return null;
  return num(value) ?? undefined;
}

export function parseLocalEngine(raw: unknown): LocalEngine | null {
  const o = asRecord(raw);
  if (!o) return null;
  const kind = str(o.kind);
  switch (kind) {
    case "unsupported": {
      const reason = str(o.reason);
      const detail = str(o.detail);
      if (reason == null || detail == null) return null;
      return { kind, reason, detail };
    }
    case "not_installed": {
      const model = parseModelCard(o.model);
      const download_bytes = num(o.download_bytes);
      if (!model || download_bytes == null) return null;
      return { kind, model, download_bytes };
    }
    case "acquiring": {
      const model = parseModelCard(o.model);
      const step = str(o.step);
      const done_bytes = num(o.done_bytes);
      const total_bytes = num(o.total_bytes);
      const eta_s = parseEta(o.eta_s);
      if (!model || step == null || done_bytes == null || total_bytes == null || eta_s === undefined) {
        return null;
      }
      return { kind, model, step, done_bytes, total_bytes, eta_s };
    }
    case "starting": {
      const model = parseModelCard(o.model);
      const elapsed_s = num(o.elapsed_s);
      if (!model || elapsed_s == null) return null;
      return { kind, model, elapsed_s };
    }
    case "ready": {
      const model = parseModelCard(o.model);
      const started_at = num(o.started_at);
      if (!model || started_at == null) return null;
      return { kind, model, started_at };
    }
    case "failed": {
      const stage = str(o.stage);
      const message = str(o.message);
      const retryable = bool(o.retryable);
      if (stage == null || message == null || retryable == null) return null;
      return { kind, stage, message, retryable };
    }
    default:
      return null;
  }
}
