import { readFileSync, existsSync, readdirSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..");
const scratch = process.env.SCRATCH_DIR ?? root;
process.chdir(root);

console.log("=== vitest (all tests) ===");
const testOut = execSync("npm test", { encoding: "utf8" });
console.log(testOut);
const testMatch = testOut.match(/Tests\s+(\d+) passed/);
if (!testMatch) throw new Error("vitest did not report pass count");
console.log(`OK vitest: ${testMatch[1]} passed`);

const sourceFiles = [
  "src/lib/components/editor/NoteEditor.svelte",
  "src/lib/editor/note-save.ts",
  "src/lib/editor/wikilink-click.ts",
  "src/lib/editor/wikilink-extension.ts",
  "src/lib/vault/search-dispatch.ts",
  "src/lib/vault/markdown.ts",
  "src/lib/components/vault/VaultSidebar.svelte",
];

for (const rel of sourceFiles) {
  if (!existsSync(resolve(root, rel))) throw new Error(`missing shipped source: ${rel}`);
  console.log(`OK exists ${rel}`);
}

const noteEditor = readFileSync(resolve(root, "src/lib/components/editor/NoteEditor.svelte"), "utf8");
if (!noteEditor.includes("serializeEditorHtmlToNote")) throw new Error("NoteEditor missing save helper");
if (!noteEditor.includes("activateWikilinkTarget")) throw new Error("NoteEditor missing wikilink helper");
if (!noteEditor.includes("vaultRefreshNonce")) throw new Error("NoteEditor missing vault refresh effect");
if (!noteEditor.includes("refreshVaultFiles")) throw new Error("NoteEditor missing refreshVaultFiles");

const dispatch = readFileSync(resolve(root, "src/lib/vault/search-dispatch.ts"), "utf8");
if (!dispatch.includes("resolveSemanticSourcePath")) throw new Error("search-dispatch missing path resolver");

const gitFiles = execSync("git ls-files desktop/", { cwd: repoRoot, encoding: "utf8" })
  .trim()
  .split("\n")
  .filter(Boolean);
writeFileSync(resolve(scratch, "git-desktop-files.txt"), gitFiles.join("\n"));
console.log(`OK git tracks ${gitFiles.length} desktop files`);

const indexHtml = readFileSync(resolve(root, "build/index.html"), "utf8");
if (!indexHtml.includes("_app")) throw new Error("build missing bundles");

const nodesDir = resolve(root, "build/_app/immutable/nodes");
const nodeFile = readdirSync(nodesDir).find((f) => f.startsWith("2."));
const bundle = readFileSync(resolve(nodesDir, nodeFile), "utf8");
if (!bundle.includes("wikiLink")) throw new Error("bundle missing wikiLink mark");

console.log("logic-exercise complete");