#!/usr/bin/env bash
# Run plan verification steps and copy artifacts to SCRATCH_DIR.
set -euo pipefail

DESKTOP="$(cd "$(dirname "$0")/.." && pwd)"
SCRATCH="${SCRATCH_DIR:-$DESKTOP/../.verify-scratch}"
PHASE_BASE="${PHASE_BASE_COMMIT:-4d95531}"

mkdir -p "$SCRATCH"
cd "$DESKTOP"

echo "=== vitest ===" | tee "$SCRATCH/test.log"
npm run test 2>&1 | tee -a "$SCRATCH/test.log"

echo "=== svelte-check ===" | tee "$SCRATCH/check.log"
npm run check 2>&1 | tee -a "$SCRATCH/check.log"

echo "=== build 1 ===" | tee "$SCRATCH/build-run-1.log"
npm run build 2>&1 | tee -a "$SCRATCH/build-run-1.log"

echo "=== build 2 ===" | tee "$SCRATCH/build-run-2.log"
npm run build 2>&1 | tee -a "$SCRATCH/build-run-2.log"

test -f build/index.html
ls build/_app/immutable/entry/*.js >> "$SCRATCH/build-run-2.log"

echo "=== playwright layout ===" | tee "$SCRATCH/playwright-run.log"
SCRATCH_DIR="$SCRATCH" npm run verify:layout 2>&1 | tee -a "$SCRATCH/playwright-run.log"

echo "=== sidecar contract ===" | tee "$SCRATCH/sidecar-run.log"
SCRATCH_DIR="$SCRATCH" npm run verify:sidecar 2>&1 | tee -a "$SCRATCH/sidecar-run.log"

cp scripts/verify-layout.mjs "$SCRATCH/verify-layout.mjs"
cp scripts/verify-sidecar-contract.py "$SCRATCH/verify-sidecar-contract.py"
cp scripts/capture-evidence.sh "$SCRATCH/capture-evidence.sh"

ls -1 src/lib/components/workspace/ | tee "$SCRATCH/workspace-components.txt"
git -C "$(dirname "$DESKTOP")" diff --name-only "$PHASE_BASE" HEAD -- desktop/ | tee "$SCRATCH/changed-files.txt"

grep -E "Tests +[0-9]+ passed" "$SCRATCH/test.log" | tail -1 | tee "$SCRATCH/test-count.txt"

echo "=== emit completion ===" | tee "$SCRATCH/emit-completion.log"
SCRATCH_DIR="$SCRATCH" node scripts/emit-completion.mjs | tee "$SCRATCH/completion.md" > GOAL_EVIDENCE.md
cp GOAL_EVIDENCE.md "$SCRATCH/completion.md"

echo "Evidence captured in $SCRATCH"
echo "GOAL_EVIDENCE.md written in $DESKTOP"