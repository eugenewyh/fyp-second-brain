/** Strip wrappers so auth UI shows a short human message. */

export function formatAuthError(raw: unknown, fallback = "Could not sign in"): string {
  const text =
    raw instanceof Error ? raw.message : typeof raw === "string" ? raw : fallback;
  const trimmed = text.trim();
  if (!trimmed) return fallback;

  const jsonMatch = trimmed.match(/\{[\s\S]*\}$/);
  if (jsonMatch) {
    try {
      const payload = JSON.parse(jsonMatch[0]) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        return payload.detail.trim();
      }
    } catch {
      /* ignore */
    }
  }

  const httpPrefix = trimmed.match(
    /^Cloud (?:Watch|Scheduled Research) HTTP \d+:\s*(.+)$/i,
  );
  if (httpPrefix?.[1] && !httpPrefix[1].startsWith("{")) {
    return httpPrefix[1].trim();
  }

  if (
    /^Cloud (?:Watch|Scheduled Research) unreachable/i.test(trimmed) ||
    /URLError/i.test(trimmed)
  ) {
    return "Can't reach Cloud Scheduled Research right now.";
  }

  return trimmed;
}
