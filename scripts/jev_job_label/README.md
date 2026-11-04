# Jev job-router labeling (Vercel AI Gateway)

Pseudo-label Manager jobs (`file` / `answer` / `research` / `refuse`) with **TypeSafe Jev** (`typesafe-ai/jev`) through Vercel AI Gateway, then merge into the supervised training set.

## One-time setup

1. Vercel account + AI Gateway access.
2. **Add a credit card** on the team (required to unlock free Gateway credits):  
   https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%3Fmodal%3Dadd-credit-card  
   Without this, Jev calls return `customer_verification_required`.
3. Stay on **Hobby** if you want — do **not** enable Zero Data Retention (`providerOptions.gateway.zeroDataRetention`); that needs Pro.
4. Create an API key (dashboard) **or** run:

   ```bash
   npx vercel@latest ai-gateway setup
   ```

5. Put the key in the **repo root** `.env` (gitignored):

   ```bash
   AI_GATEWAY_API_KEY=your_key_here
   ```

6. Install deps:

   ```bash
   cd scripts/jev_job_label
   npm install
   ```

7. Smoke test:

   ```bash
   npm run smoke
   ```

## Label → merge → retrain

```bash
# from repo root
python3 scripts/generate_unlabeled_job_candidates.py

cd scripts/jev_job_label
npm run label -- --limit 20                 # dry batch
npm run label -- --min-confidence 0.7       # full candidates

cd ../..
python3 scripts/merge_jev_labels.py --min-confidence 0.85
python3 scripts/train_job_router.py
python3 scripts/eval_job_router.py
```

High-confidence Jev rows are **teacher labels**. Spot-check a sample before trusting the merge for thesis numbers.
