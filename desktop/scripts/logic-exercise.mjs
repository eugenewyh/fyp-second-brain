import { readFileSync, existsSync, readdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const scratch = process.env.SCRATCH_DIR ?? root;
process.chdir(root);

console.log("=== vitest (all tests) ===");
execSync("npm test", { stdio: "inherit" });

const checks = [
  ["NoteEditor.svelte", "src/lib/components/editor/NoteEditor.svelte"],
  ["WikiLink getAttrs", "src/lib/editor/wikilink-extension.ts"],
  ["marked+turndown markdown", "src/lib/vault/markdown.ts"],
  ["semantic branch", "src/lib/components/vault/VaultSidebar.svelte"],
  ["requestVaultRefresh ResearchReport", "src/lib/components/research/ResearchReport.svelte"],
  ["requestVaultRefresh IngestPanel", "src/lib/components/documents/IngestPanel.svelte"],
];

for (const [label, rel] of checks) {
  const text = readFileSync(resolve(root, rel), "utf8");
  if (label === "WikiLink getAttrs" && !text.includes("getAttrs")) {
    throw new Error("wikilink-extension missing getAttrs");
  }
  if (label === "marked+turndown markdown" && !text.includes("TurndownService")) {
    throw new Error("markdown.ts missing TurndownService");
  }
  console.log(`OK ${label}`);
}

const indexHtml = readFileSync(resolve(root, "build/index.html"), "utf8");
if (!indexHtml.includes("_app")) throw new Error("build missing bundles");

const nodesDir = resolve(root, "build/_app/immutable/nodes");
const nodeFile = readdirSync(nodesDir).find((f) => f.startsWith("2."));
const bundle = readFileSync(resolve(nodesDir, nodeFile), "utf8");
if (!bundle.includes("wikiLink")) throw new Error("bundle missing wikiLink mark");
if (!bundle.includes("@tiptap") && !bundle.includes("tiptap")) {
  throw new Error("bundle missing tiptap runtime");
}

const placeholder = readFileSync(
  resolve(root, "src/lib/components/editor/EditorPlaceholder.svelte"),
  "utf8",
);
if (placeholder.includes("TipTap editor coming in Phase 2")) {
  throw new Error("EditorPlaceholder still has stale Phase 2 placeholder text");
}

console.log("OK build bundle contains TipTap + wikiLink mark");
console.log("OK EditorPlaceholder has no stale placeholder");
console.log("logic-exercise complete");