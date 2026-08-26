/** Short vault-folder name from a user request. Mirrors the Manager heuristic. */

const LEAD =
  /^(?:please\s+)?(?:find|search(?:\s+for)?|look\s*up|watch(?:\s+for)?|research|read(?:\s+about)?|summarise|summarize|explain|help\s+(?:me\s+)?(?:with\s+)?)\s+/i;
const PAPERS_ON = /^(?:papers?|articles?|literature|sources?)\s+(?:on|about)\s+/i;
const ON_ABOUT = /^(?:on|about|regarding|re)\s+/i;
const MY_WORK = /\b(?:my|our)\s+(fyp|thesis|dissertation|project|paper)\b/i;

export function suggestTopicName(text: string): string {
  let blob = (text || "").trim().split("\n")[0] ?? "";
  blob = blob.replace(/[?.!]+$/, "").trim();
  if (!blob) return "Research";
  const mine = MY_WORK.exec(blob);
  if (mine) {
    const word = mine[1] ?? "Research";
    return word.toLowerCase() === "fyp" ? "FYP" : word[0]!.toUpperCase() + word.slice(1);
  }
  blob = blob.replace(LEAD, "");
  blob = blob.replace(PAPERS_ON, "");
  blob = blob.replace(ON_ABOUT, "");
  blob = blob.replace(/[\\/:*?"<>|]+/g, " ").replace(/\s+/g, " ").trim();
  const words = blob.split(" ").filter(Boolean);
  if (!words.length) return "Research";
  let clipped = words.slice(0, 6).join(" ");
  if (clipped.length > 48) clipped = clipped.slice(0, 48).replace(/\s+\S*$/, "") || clipped.slice(0, 48);
  if (["this", "it", "help", "please", "stuff"].includes(clipped.toLowerCase())) return "Research";
  return clipped;
}
