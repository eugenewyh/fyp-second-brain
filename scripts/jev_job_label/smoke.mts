/** One-shot Jev call to verify AI_GATEWAY_API_KEY works. */

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { experimental_evaluate as evaluate } from "ai";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

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

loadEnvFile(resolve(ROOT, ".env"));
loadEnvFile(resolve(ROOT, ".env.local"));

if (!process.env.AI_GATEWAY_API_KEY?.trim()) {
  console.error("Set AI_GATEWAY_API_KEY in repo-root .env first.");
  process.exit(1);
}

const result = await evaluate({
  model: "typesafe-ai/jev",
  state: {
    user_message: "According to my notes, what grind size should I use for espresso?",
    matching_claim_count: 5,
    has_attachments: false,
  },
  questions: {
    job: {
      type: "choice",
      instructions: "Which Manager job?",
      criteria: {
        file: "Teach / remember notes",
        answer: "Ask from notes",
        research: "Research outside vault",
        refuse: "Refuse empty memory ask",
      },
    },
  },
});

console.log(JSON.stringify(result.answers, null, 2));
console.log("OK — Jev via AI Gateway is working.");
