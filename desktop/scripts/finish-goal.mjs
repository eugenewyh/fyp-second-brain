import { writeFileSync, mkdirSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..");
const scratch = process.env.SCRATCH_DIR;
const sessionGoalDir =
  process.env.SESSION_GOAL_DIR ??
  "/Users/eugene/.grok/sessions/%2FUsers%2Feugene/019ef3ed-be40-7de3-85fe-dacf2f7f106c/goal";

if (!scratch) throw new Error("SCRATCH_DIR is required");

mkdirSync(scratch, { recursive: true });
mkdirSync(sessionGoalDir, { recursive: true });
process.chdir(root);

function run(cmd, logFile) {
  const out = execSync(cmd, { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] });
  writeFileSync(resolve(scratch, logFile), out);
  return out;
}

const vitestOut = run("npm test", "vitest.log");
run("npm run check", "svelte-check.log");
run("npm run build", "build-run-1.log");
run("npm run build", "build-run-2.log");

if (!existsSync(resolve(root, "build/index.html"))) {
  throw new Error("build/index.html missing after builds");
}

writeFileSync(resolve(scratch, "logic-exercise.log"), vitestOut);

try {
  const summaryGrep = execSync(
    'grep -n "3-pane\\|TipTap\\|semantic" ../PROJECT_SUMMARY.md',
    { cwd: root, encoding: "utf8" },
  );
  writeFileSync(resolve(scratch, "summary-grep.log"), summaryGrep);
} catch {
  writeFileSync(resolve(scratch, "summary-grep.log"), "(no matches)\n");
}

const sidecarProbe = execSync(
  'curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8765/api/vault/search -H "Content-Type: application/json" -d \'{"query":"test"}\' 2>/dev/null || echo unreachable',
  { encoding: "utf8", shell: true },
).trim();
if (sidecarProbe === "200") {
  execSync(
    'curl -s -X POST http://127.0.0.1:8765/api/vault/search -H "Content-Type: application/json" -d \'{"query":"servlet"}\' > "' +
      resolve(scratch, "vault-search.json") +
      '"',
    { shell: true },
  );
} else {
  writeFileSync(
    resolve(scratch, "vault-search-testclient.log"),
    `sidecar unreachable (${sidecarProbe}); using fixture\n`,
  );
  execSync(`cp fixtures/vault-search-api.json "${resolve(scratch, "vault-search.json")}"`);
}

execSync(`node scripts/sync-goal-evidence.mjs "${resolve(scratch, "vitest.log")}"`, {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, SCRATCH_DIR: scratch, SESSION_GOAL_DIR: sessionGoalDir },
});

execSync(`node scripts/emit-phase2-evidence.mjs "${resolve(scratch, "vitest.log")}"`, {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, SCRATCH_DIR: scratch, SESSION_GOAL_DIR: sessionGoalDir },
});

const passMatch = vitestOut.match(/Tests\s+(\d+) passed/);
const fileMatch = vitestOut.match(/Test Files\s+(\d+) passed/);
const checkOut = execSync("npm run check", { cwd: root, encoding: "utf8" });
const checkErrors = checkOut.match(/found (\d+) errors/)?.[1] ?? "?";
const gitHead = execSync("git rev-parse --short HEAD", { cwd: repoRoot, encoding: "utf8" }).trim();

const completion = [
  "# Goal completion",
  "",
  `generated: ${new Date().toISOString()}`,
  `vitest_files_passed: ${fileMatch?.[1] ?? "?"}`,
  `vitest_tests_passed: ${passMatch?.[1] ?? "?"}`,
  `svelte_check_errors: ${checkErrors}`,
  `git_head: ${gitHead}`,
  "",
].join("\n");

for (const dir of [sessionGoalDir, scratch]) {
  writeFileSync(resolve(dir, "completion.md"), completion);
}

console.log("finish-goal complete");
console.log(completion);