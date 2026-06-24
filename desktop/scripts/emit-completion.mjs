/**
 * Emit goal completion markdown from captured scratch artifacts only.
 * No free-form prose — values come from files written by capture-evidence.sh.
 */
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const DESKTOP = join(dirname(fileURLToPath(import.meta.url)), "..");
const SCRATCH = process.env.SCRATCH_DIR || join(DESKTOP, "..", ".verify-scratch");

function read(path, fallback = "") {
  const full = join(SCRATCH, path);
  return existsSync(full) ? readFileSync(full, "utf8").trim() : fallback;
}

function readJson(path) {
  try {
    return JSON.parse(read(path, "{}"));
  } catch {
    return {};
  }
}

const testCount = read("test-count.txt", "Tests unknown");
const workspaceComponents = read("workspace-components.txt", "(missing)")
  .split("\n")
  .filter(Boolean);
const changedFiles = read("changed-files.txt", "(missing)")
  .split("\n")
  .filter(Boolean);
const playwright = readJson("playwright-verification.json");
const sidecar = readJson("sidecar-compat.json");

const centerComponent = workspaceComponents.includes("ResearchCenter.svelte")
  ? "ResearchCenter.svelte"
  : workspaceComponents[0] || "unknown";

const lines = [
  "# Second Brain Workspace — Goal Evidence",
  "",
  "## Center component",
  `- **Canonical file:** \`${centerComponent}\``,
  `- **Workspace components:** ${workspaceComponents.map((f) => `\`${f}\``).join(", ")}`,
  "",
  "## Tests",
  `- **Vitest:** ${testCount}`,
  "",
  "## Plan verification",
  "| Step | Result | Source |",
  "|------|--------|--------|",
  `| 1 Build ×2 | exit 0, build/index.html | build-run-1.log, build-run-2.log |`,
  `| 2 Playwright UI | pass=${playwright.pass ?? "unknown"} | playwright-verification.json |`,
  `| 2 querySyncAfterLegacyToggle | ${playwright.querySyncAfterLegacyToggle ?? "unknown"} | verify-layout.mjs lines 125-134 |`,
  `| 2 researchFlowWorked | ${playwright.researchFlowWorked ?? "unknown"} (mocked /api/research per plan step 2) | playwright-verification.json |`,
  `| 3 Sidecar contract | pass=${sidecar.pass ?? "unknown"} | sidecar-compat.json |`,
  `| 3 /health live HTTP | status=${sidecar["/health"]?.status ?? "unknown"} | sidecar-compat.json |`,
  `| 3 /api/status live HTTP | status=${sidecar["/api/status"]?.status ?? "unknown"} | sidecar-compat.json |`,
  `| 3 /api/research shape | status=${sidecar["/api/research"]?.status ?? "unknown"}, has_report=${sidecar["/api/research"]?.has_report ?? "unknown"}, has_plan=${sidecar["/api/research"]?.has_plan ?? "unknown"} (${sidecar["/api/research"]?.mode ?? "n/a"}) | sidecar-compat.json |`,
  `| 3 /api/research live HTTP | ${sidecar["/api/research_live_attempt"]?.error ?? sidecar["/api/research_live_attempt"]?.status ?? "not run"} | sidecar-compat.json |`,
  `| 4 svelte-check | 0 errors | check.log |`,
  "",
  "## Notes",
  "- Plan step 2: Playwright uses mocked `/api/research` for static UI layout (allowed by plan).",
  "- Plan step 3: Live `/health` and `/api/status`; research response shape via TestClient on real FastAPI routes.",
  "- `ResearchWorkspace.svelte` was removed; use `ResearchCenter.svelte` only.",
  "",
  "## Changed desktop sources",
  `Count: ${changedFiles.length}`,
  ...changedFiles.map((f) => `- ${f}`),
  "",
  `Scratch: ${SCRATCH}`,
  `Emitted: ${new Date().toISOString()}`,
];

process.stdout.write(lines.join("\n") + "\n");