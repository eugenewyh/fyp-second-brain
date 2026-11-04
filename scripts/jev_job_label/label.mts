/**
 * Pseudo-label Manager job-router turns with TypeSafe Jev via Vercel AI Gateway.
 *
 * Usage (from this directory):
 *   export AI_GATEWAY_API_KEY=...   # or put in repo-root .env
 *   npm run label -- --limit 20
 *   npm run label -- --min-confidence 0.85 --dry-run
 *
 * Then merge high-confidence rows:
 *   python3 ../merge_jev_labels.py
 *   python3 ../train_job_router.py
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { experimental_evaluate as evaluate } from "ai";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "../..");
const DEFAULT_INPUT = resolve(ROOT, "data/job_router/unlabeled_candidates.json");
const DEFAULT_OUT = resolve(ROOT, "data/job_router/jev_proposals.json");
const LABELED = resolve(ROOT, "data/job_router/labeled_turns.json");

const JOBS = ["file", "answer", "research", "refuse"] as const;
type Job = (typeof JOBS)[number];

type Candidate = {
  text: string;
  claims?: number;
  attachments?: boolean;
};

type Proposal = Candidate & {
  job: Job;
  confidence: number;
  probabilities: Record<string, number>;
  source: "jev";
  model: string;
};

function loadEnvFile(path: string): void {
  if (!existsSync(path)) return;
  for (const line of readFileSync(path, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 0) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = val;
  }
}

function parseArgs(argv: string[]) {
  const out = {
    input: DEFAULT_INPUT,
    out: DEFAULT_OUT,
    minConfidence: 0,
    limit: 0,
    dryRun: false,
    sleepMs: 50,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--input") out.input = resolve(argv[++i]!);
    else if (a === "--out") out.out = resolve(argv[++i]!);
    else if (a === "--min-confidence") out.minConfidence = Number(argv[++i]);
    else if (a === "--limit") out.limit = Number(argv[++i]);
    else if (a === "--sleep-ms") out.sleepMs = Number(argv[++i]);
    else if (a === "--dry-run") out.dryRun = true;
    else if (a === "--help" || a === "-h") {
      console.log(`Usage: npm run label -- [options]
  --input PATH           unlabeled candidates JSON (default: data/job_router/unlabeled_candidates.json)
  --out PATH             write proposals here (default: data/job_router/jev_proposals.json)
  --min-confidence N     only keep proposals with confidence >= N (default: 0, keep all)
  --limit N              max candidates to label (0 = all)
  --sleep-ms N           pause between calls (default: 50)
  --dry-run              print first result and exit`);
      process.exit(0);
    }
  }
  return out;
}

function loadCandidates(path: string): Candidate[] {
  const raw = JSON.parse(readFileSync(path, "utf8"));
  if (!Array.isArray(raw)) throw new Error(`${path} must be a JSON array`);
  return raw
    .map((r) => ({
      text: String(r?.text ?? "").trim(),
      claims: Number(r?.claims ?? 0),
      attachments: Boolean(r?.attachments),
    }))
    .filter((r) => r.text.length > 0);
}

function existingTexts(): Set<string> {
  if (!existsSync(LABELED)) return new Set();
  const rows = JSON.parse(readFileSync(LABELED, "utf8")) as Array<{ text?: string }>;
  return new Set(rows.map((r) => String(r.text ?? "").trim()).filter(Boolean));
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function labelOne(c: Candidate): Promise<Proposal> {
  const result = await evaluate({
    model: "typesafe-ai/jev",
    state: {
      product: "Nous Second Brain",
      manager_jobs: {
        file: "Teach: user is dumping notes, pasting content, or asking to remember/save into topic memory",
        answer: "Ask: user wants an answer grounded in existing notes/claims for this topic",
        research:
          "Research: user wants outside lookup, papers, web, a report, comparison, or multi-step investigation. " +
          "If the message uses research as a command (research this, research that, research X, please research, " +
          "can you research) ALWAYS choose research — not answer or file.",
        refuse:
          "Refuse: vault/topic memory is empty or too thin for a notes-grounded ask; do not invent personal facts",
      },
      matching_claim_count: c.claims ?? 0,
      has_attachments: Boolean(c.attachments),
      user_message: c.text,
    },
    questions: {
      job: {
        type: "choice",
        instructions:
          "Which Manager job should handle user_message, given matching_claim_count and has_attachments? " +
          "Imperative research phrasing (research this/that/it/the…, please research, can you research) → research.",
        criteria: {
          file: "Teach / remember / file notes or attachments into memory (not 'research this')",
          answer: "Ask / recall from existing notes; never when user said research this/that",
          research:
            "Research / search outside / write a cited report — including any 'research this/that/X' command",
          refuse: "Refuse when Ask is requested but memory is empty/thin",
        },
      },
    },
  });

  const answer = result.answers.job;
  if (!answer || answer.type !== "choice") {
    throw new Error(`Unexpected answer shape: ${JSON.stringify(answer)}`);
  }
  const job = String(answer.choice) as Job;
  if (!JOBS.includes(job)) {
    throw new Error(`Invalid job from Jev: ${job}`);
  }

  const confidenceMeta =
    (result.providerMetadata as { typesafe?: { confidence?: Record<string, number> } } | undefined)
      ?.typesafe?.confidence?.job ?? Number(answer.confidence ?? 0);

  return {
    text: c.text,
    claims: c.claims ?? 0,
    attachments: Boolean(c.attachments),
    job,
    confidence: Number(confidenceMeta),
    probabilities: Object.fromEntries(
      Object.entries(answer.probabilities ?? {}).map(([k, v]) => [k, Number(v)]),
    ),
    source: "jev",
    model: "typesafe-ai/jev",
  };
}

async function main() {
  loadEnvFile(resolve(ROOT, ".env"));
  loadEnvFile(resolve(ROOT, ".env.local"));

  if (!process.env.AI_GATEWAY_API_KEY?.trim()) {
    console.error(`Missing AI_GATEWAY_API_KEY.

1. Create a key: https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%2Fapi-keys
   or run:  npx vercel@latest ai-gateway setup
2. Add to repo-root .env:
   AI_GATEWAY_API_KEY=...
`);
    process.exit(1);
  }

  const args = parseArgs(process.argv.slice(2));
  if (!existsSync(args.input)) {
    console.error(`Input not found: ${args.input}`);
    process.exit(1);
  }

  const known = existingTexts();
  let candidates = loadCandidates(args.input).filter((c) => !known.has(c.text));
  if (args.limit > 0) candidates = candidates.slice(0, args.limit);

  console.log(`Labeling ${candidates.length} candidates with typesafe-ai/jev…`);

  const proposals: Proposal[] = [];
  let skippedLow = 0;

  for (let i = 0; i < candidates.length; i++) {
    const c = candidates[i]!;
    process.stdout.write(`[${i + 1}/${candidates.length}] ${c.text.slice(0, 72)}… `);
    try {
      const p = await labelOne(c);
      if (args.dryRun) {
        console.log("\n", JSON.stringify(p, null, 2));
        return;
      }
      if (p.confidence < args.minConfidence) {
        skippedLow += 1;
        console.log(`skip (conf=${p.confidence.toFixed(3)} < ${args.minConfidence}) → ${p.job}`);
      } else {
        proposals.push(p);
        console.log(`→ ${p.job} (conf=${p.confidence.toFixed(3)})`);
      }
    } catch (err) {
      console.log("ERROR");
      const msg = err instanceof Error ? err.message : String(err);
      const body = typeof err === "object" && err && "responseBody" in err
        ? String((err as { responseBody?: string }).responseBody ?? "")
        : msg;
      if (/credit card|customer_verification_required/i.test(body + msg)) {
        console.error(`
AI Gateway blocked the request: add a credit card to unlock free credits.
Open: https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%3Fmodal%3Dadd-credit-card

Until then, labeling cannot run (no jev_proposals.json will be written).
Do not run merge/train expecting new Jev labels yet.
`);
      }
      console.error(err);
      process.exit(1);
    }
    if (args.sleepMs > 0) await sleep(args.sleepMs);
  }

  writeFileSync(args.out, JSON.stringify(proposals, null, 2) + "\n", "utf8");
  console.log(
    `\nWrote ${proposals.length} proposals to ${args.out}` +
      (skippedLow ? ` (${skippedLow} below min-confidence)` : ""),
  );
  console.log(`Next: python3 scripts/merge_jev_labels.py && python3 scripts/train_job_router.py`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
