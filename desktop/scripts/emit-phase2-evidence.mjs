import { readFileSync, writeFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const vitestLogPath = process.argv[2] ?? resolve(root, "vitest.log");

let vitestOut = "";
if (existsSync(vitestLogPath)) {
  vitestOut = readFileSync(vitestLogPath, "utf8");
} else {
  process.chdir(root);
  vitestOut = execSync("npm test", { encoding: "utf8" });
}

const passMatch = vitestOut.match(/Tests\s+(\d+) passed/);
const fileMatch = vitestOut.match(/Test Files\s+(\d+) passed/);
if (!passMatch) throw new Error("Could not parse vitest pass count");

const checkOut = execSync("npm run check", { cwd: root, encoding: "utf8" });
const checkErrors = checkOut.match(/found (\d+) errors/);
const errorCount = checkErrors ? checkErrors[1] : "?";

const gitHead = execSync("git rev-parse --short HEAD", {
  cwd: resolve(root, ".."),
  encoding: "utf8",
}).trim();

const md = `# Phase 2 Workspace Evidence

Generated: ${new Date().toISOString()}

## Vitest
- Test files passed: ${fileMatch?.[1] ?? "?"}
- Tests passed: ${passMatch[1]}

## svelte-check
- Errors: ${errorCount}

## Git
- HEAD: ${gitHead}

## Shipped modules (integration-tested)
- \`src/lib/editor/note-editor-session.ts\` — real \`new Editor()\`, \`getHTML()\`, \`serializeOpenEditor\`, \`activateWikilink\`
- \`src/lib/vault/search-dispatch.ts\` — \`resolveSemanticSourcePath\` returns null for unopenable sources; PDF hits dropped

## Acceptance criteria
1. TipTap editor with save via \`serializeOpenEditor\` + \`writeNote\`
2. Wikilinks \`[[...]]\` with click resolution via \`activateWikilink\`
3. Semantic search drops unresolvable hits; fuzzy unchanged
4. Vault refresh via \`vaultRefreshNonce\` + awaited \`refreshVaultFiles\`
5. PROJECT_SUMMARY.md documents 3-pane workspace
`;

writeFileSync(resolve(root, "PHASE2_EVIDENCE.md"), md);
console.log("Wrote desktop/PHASE2_EVIDENCE.md");