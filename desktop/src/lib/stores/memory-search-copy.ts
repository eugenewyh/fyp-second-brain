/** User-facing copy for vault-search / embedding failures. */
export function memorySearchErrorCopy(raw: string | undefined | null): string {
  const text = (raw || "").trim();
  if (!text) return "Vault search unavailable";
  const lower = text.toLowerCase();
  if (
    lower === "load failed" ||
    lower === "failed to fetch" ||
    /networkerror|network request failed|econnrefused/i.test(lower)
  ) {
    return "Could not reach the AI service while loading search. Retry in a moment.";
  }
  if (
    /no_suchfile|model_optimized\.onnx|\.incomplete|missing or incomplete|load model/i.test(
      lower,
    )
  ) {
    return "Local search model is incomplete. Retry to re-download it.";
  }
  if (text.length > 160) return `${text.slice(0, 157)}…`;
  return text;
}
