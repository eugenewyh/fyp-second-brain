import { execSync } from "child_process";
import { existsSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..");
const scratch = process.env.SCRATCH_DIR ?? root;

process.chdir(root);

const lines = [];

function section(title) {
  lines.push(`\n=== ${title} ===\n`);
  console.log(`=== ${title} ===`);
}

function run(cmd, cwd = root) {
  const out = execSync(cmd, { cwd, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] });
  lines.push(out);
  console.log(out);
  return out;
}

section("shipped file existence");
const shipped = [
  "src/lib/editor/note-editor-session.ts",
  "src/lib/editor/note-editor-session.test.ts",
  "src/lib/editor/wikilink-extension.ts",
  "src/lib/components/editor/NoteEditor.svelte",
  "src/lib/vault/search-dispatch.ts",
  "src/lib/vault/markdown.ts",
  "src/lib/vault/wikilinks.ts",
  "fixtures/vault-search-api.json",
];
for (const rel of shipped) {
  const ok = existsSync(resolve(root, rel));
  const line = `${rel}: ${ok ? "OK" : "MISSING"}`;
  lines.push(`${line}\n`);
  console.log(line);
}

section("vitest — shipped module tests (real imports)");
run(
  "npx vitest run src/lib/editor/note-editor-session.test.ts src/lib/components/editor/NoteEditor.test.ts src/lib/vault/search-dispatch.test.ts src/lib/vault/markdown.test.ts src/lib/vault/wikilinks.test.ts --reporter=verbose",
);

section("source grep — vault refresh hooks");
run(
  'grep -n "requestVaultRefresh" src/lib/components/research/ResearchReport.svelte src/lib/components/documents/IngestPanel.svelte src/lib/components/editor/NoteEditor.svelte',
);

section("source grep — semantic search dispatch");
run(
  'grep -n "shouldUseSemanticSearch\\|vaultSearchMode\\|vaultSearch\\|semanticSearchHits" src/lib/components/vault/VaultSidebar.svelte src/lib/vault/search-dispatch.ts',
);

section("source grep — TipTap editor path");
run(
  'grep -n "createEditorFromMarkdown\\|serializeOpenEditor\\|activateWikilink\\|writeNote" src/lib/components/editor/NoteEditor.svelte src/lib/editor/note-editor-session.ts',
);

section("npm test (full suite)");
const testOut = run("npm test");

section("npm run check");
const checkOut = run("npm run check");

section("npm run build");
const buildOut = run("npm run build");

writeFileSync(resolve(scratch, "logic-exercise.log"), lines.join(""));

writeFileSync(
  resolve(scratch, "summary-grep.log"),
  execSync(
    'grep -n "3-pane\\|TipTap\\|semantic\\|wikilink\\|Vault sidebar" ../PROJECT_SUMMARY.md',
    { cwd: root, encoding: "utf8" },
  ),
);

execSync(`node scripts/sync-goal-evidence.mjs "${resolve(scratch, "vitest.log")}"`, {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, SCRATCH_DIR: scratch },
});

console.log("logic-exercise complete");