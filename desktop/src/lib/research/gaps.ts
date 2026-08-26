/** Extract open questions / gaps from a research report for follow-up learning. */

export function extractOpenQuestions(report: string, max = 4): string[] {
  if (!report.trim()) return [];

  const sectionMatch = report.match(
    /(?:^|\n)##?\s*(?:(?:identified\s+)?gaps?|what'?s missing)[^\n]*\n([\s\S]*?)(?=\n##\s|\n#\s|$)/i,
  );
  const block = sectionMatch?.[1] ?? report;

  const bullets = block
    .split("\n")
    .map((line) => line.replace(/^[\s>*\-•\d.]+/, "").trim())
    .filter((line) => line.length > 24 && line.length < 220)
    .filter((line) => !/^sources?\b/i.test(line));

  const unique: string[] = [];
  for (const b of bullets) {
    if (!unique.some((u) => u.toLowerCase() === b.toLowerCase())) unique.push(b);
    if (unique.length >= max) break;
  }
  return unique;
}

export function questionFromGap(gap: string): string {
  const cleaned = gap.replace(/\.$/, "");
  if (/\?$/.test(cleaned)) return cleaned;
  return `Based on my library and prior research: ${cleaned}`;
}
