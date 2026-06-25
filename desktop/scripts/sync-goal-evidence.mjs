import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..");
const scratch = process.env.SCRATCH_DIR ?? resolve(repoRoot, ".verify-scratch");
const sessionGoalDir =
  process.env.SESSION_GOAL_DIR ??
  "/Users/eugene/.grok/sessions/%2FUsers%2Feugene/019ef3ed-be40-7de3-85fe-dacf2f7f106c/goal";
const phaseBase = process.env.PHASE_BASE_COMMIT ?? "2825360";

mkdirSync(scratch, { recursive: true });
mkdirSync(sessionGoalDir, { recursive: true });

const vitestLog = process.argv[2] ?? resolve(scratch, "vitest.log");
const vitestOut = existsSync(vitestLog) ? readFileSync(vitestLog, "utf8") : "";

const changedFiles = execSync(`git diff --name-only ${phaseBase} HEAD -- desktop/src`, {
  cwd: repoRoot,
  encoding: "utf8",
});
const changesPatch = execSync(`git diff ${phaseBase} HEAD -- desktop/src`, {
  cwd: repoRoot,
  encoding: "utf8",
});
const gitLog = execSync("git log --oneline -12", { cwd: repoRoot, encoding: "utf8" });
const gitDesktopFiles = execSync("git ls-files desktop/src", {
  cwd: repoRoot,
  encoding: "utf8",
});

const passMatch = vitestOut.match(/Tests\s+(\d+) passed/);
const fileMatch = vitestOut.match(/Test Files\s+(\d+) passed/);

const manifest = [
  "# Verifier manifest (generated from captured logs + git)",
  "",
  `vitest: ${passMatch?.[1] ?? "?"} tests passed (${fileMatch?.[1] ?? "?"} files)`,
  `git_head: ${execSync("git rev-parse --short HEAD", { cwd: repoRoot, encoding: "utf8" }).trim()}`,
  `phase_base: ${phaseBase}`,
  `changed_desktop_src_files: ${changedFiles.trim().split("\n").filter(Boolean).length}`,
  "",
  "## Changed desktop/src (git diff vs phase base)",
  changedFiles.trim(),
  "",
].join("\n");

for (const dir of [scratch, sessionGoalDir]) {
  writeFileSync(resolve(dir, "changed-files.txt"), changedFiles);
  writeFileSync(resolve(dir, "changes.patch"), changesPatch);
  writeFileSync(resolve(dir, "git-log.txt"), gitLog);
  writeFileSync(resolve(dir, "git-desktop-files.txt"), gitDesktopFiles);
  writeFileSync(resolve(dir, "verifier-manifest.txt"), manifest);
  if (passMatch) writeFileSync(resolve(dir, "test-count.txt"), passMatch[0]);
}

console.log(`Synced goal evidence to ${scratch} and ${sessionGoalDir}`);