import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const BUILD_DIR = join(ROOT, "build");
const SCRATCH = process.env.SCRATCH_DIR || join(ROOT, "..", ".verify-scratch");
const PORT = 4173;
const SIDECAR = "http://127.0.0.1:8765";

const MIME = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

const MOCK_RESEARCH = {
  query: "servlets in Java",
  plan: "1. Search personal docs\n2. Search web",
  retrieval_queries: ["[personal] servlets"],
  retrieval_stats: { personal: 3 },
  retrieval_log: ["[personal] servlets → 3 result(s)"],
  analysis: "Analysis text",
  revision_count: 0,
  report: "## Executive Summary\nServlets are Java web components.\n\n## Key Findings\n- Used for HTTP handling",
};

function startServer() {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      const urlPath = req.url?.split("?")[0] || "/";
      const filePath = join(BUILD_DIR, urlPath === "/" ? "index.html" : urlPath);
      const target = existsSync(filePath) ? filePath : join(BUILD_DIR, "index.html");
      const ext = extname(target);
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      res.end(readFileSync(target));
    });
    server.listen(PORT, () => resolve(server));
  });
}

async function main() {
  const errors = [];
  const server = await startServer();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`console: ${msg.text()}`);
  });

  await page.route(`${SIDECAR}/health`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok" }) });
  });

  await page.route(`${SIDECAR}/api/status`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        collection_count: 416,
        project_root: "/Users/eugene/fyp-second-brain",
        ollama_url: "http://localhost:11434",
      }),
    });
  });

  await page.route(`${SIDECAR}/api/research`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_RESEARCH),
      });
    } else {
      await route.continue();
    }
  });

  await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);

  const checks = {
    commandBar: await page.getByText("Ask Second Brain").count(),
    paneLeft: await page.getByTestId("pane-left").count(),
    paneCenter: await page.getByTestId("pane-center").count(),
    paneRight: await page.getByTestId("pane-right").count(),
    vaultTree: await page.getByTestId("vault-tree").count(),
    vaultRoot: await page.getByTestId("vault-tree").getAttribute("data-vault-root"),
    fuzzySearch: await page.getByTestId("fuzzy-search").count(),
    semanticSearch: await page.getByTestId("semantic-search").count(),
    graphOverview: await page.getByTestId("graph-overview").count(),
    ingestStatus: await page.getByTestId("ingest-status").count(),
    researchQuery: await page.getByTestId("research-query").count(),
    runResearch: await page.getByTestId("run-research").count(),
    splitterLeft: await page.getByTestId("splitter-left").count(),
    splitterRight: await page.getByTestId("splitter-right").count(),
    contextualChat: await page.getByTestId("contextual-chat").count(),
    backlinks: await page.getByTestId("backlinks-section").count(),
    agentLog: await page.getByTestId("agent-process-log").count(),
    sources: await page.getByTestId("sources-section").count(),
  };

  const leftWidthBefore = await page.getByTestId("pane-left").evaluate((el) => el.getBoundingClientRect().width);
  const splitter = page.getByTestId("splitter-left");
  const box = await splitter.boundingBox();
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 60, box.y + box.height / 2);
    await page.mouse.up();
    await page.waitForTimeout(100);
  }
  const leftWidthAfter = await page.getByTestId("pane-left").evaluate((el) => el.getBoundingClientRect().width);
  const widthDelta = leftWidthAfter - leftWidthBefore;

  const centerWidth = await page.getByTestId("pane-center").evaluate((el) => el.getBoundingClientRect().width);

  await page.getByTestId("research-query").fill("What are servlets in Java?");
  await page.getByTestId("run-research").click();
  await page.getByTestId("research-report").waitFor({ state: "visible", timeout: 10000 });
  const reportHeading = await page.getByTestId("research-report").locator("h2").first().textContent();
  const researchFlowWorked = reportHeading?.includes("Executive Summary") ?? false;

  const screenshotPath = join(SCRATCH, "workspace-screenshot.png");
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await browser.close();
  server.close();

  const report = {
    checks,
    leftWidthBefore,
    leftWidthAfter,
    widthDelta,
    centerWidth,
    resizeWorked: widthDelta > 10,
    centerMinOk: centerWidth >= 200,
    researchFlowWorked,
    reportHeading,
    errors,
    pass:
      errors.length === 0 &&
      Object.values(checks).every((c) => (typeof c === "string" ? c.length > 0 : c > 0)) &&
      checks.vaultRoot === "data/documents/" &&
      widthDelta > 10 &&
      centerWidth >= 200 &&
      researchFlowWorked,
  };

  writeFileSync(join(SCRATCH, "playwright-verification.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  process.exit(report.pass ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});