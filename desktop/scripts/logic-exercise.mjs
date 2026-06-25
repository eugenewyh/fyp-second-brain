import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const scratch = process.env.SCRATCH_DIR;
if (!scratch) throw new Error("SCRATCH_DIR is required — use finish-goal.mjs");

execSync("node scripts/finish-goal.mjs", {
  cwd: root,
  stdio: "inherit",
  env: process.env,
});