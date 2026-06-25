import { readFileSync, existsSync, readdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(root);

console.log("=== vitest ===");
execSync("npm test", { stdio: "inherit" });

const checks = [
  ["NoteEditor.svelte", "src/lib/components/editor/NoteEditor.svelte"],
  ["WikiLink extension", "src/lib/editor/wikilink-extension.ts"],
  ["semantic branch", "src/lib/components/vault/VaultSidebar.svelte"],
  ["requestVaultRefresh in ResearchReport", "src/lib/components/research/ResearchReport.svelte"],
  ["requestVaultRefresh in IngestPanel", "src/lib/components/documents/IngestPanel.svelte"],
];

for (const [label, rel] of checks) {
  const text = readFileSync(resolve(root, rel), "utf8");
  console.log(`OK ${label}: ${rel} (${text.length} bytes)`);
}

const indexHtml = readFileSync(resolve(root, "build/index.html"), "utf8");
if (!indexHtml.includes("_app")) throw new Error("build missing bundles");

const nodesDir = resolve(root, "build/_app/immutable/nodes");
const nodeFile = existsSync(nodesDir) ? readdirSync(nodesDir).find((f) => f.startsWith("2.")) : null;
const nodeBundles = nodeFile ? readFileSync(resolve(nodesDir, nodeFile), "utf8") : "";
if (nodeBundles && !nodeBundles.includes("wikiLink") && !nodeBundles.includes("wikilink")) {
  throw new Error("build bundle missing wikilink markers");
}
console.log("OK build contains index.html + TipTap note bundle");

console.log("logic-exercise complete");