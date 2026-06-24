#!/usr/bin/env python3
"""Plan step 3: verify sidecar HTTP contract.

- /health and /api/status: live HTTP to running sidecar
- /api/research: FastAPI TestClient on real app code with run_research mocked
  (Ollama may hang in CI/harness; mock proves response shape the UI depends on)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

SCRATCH = Path(os.environ.get("SCRATCH_DIR", ROOT / ".verify-scratch"))
SIDECAR = os.environ.get("SIDECAR_URL", "http://127.0.0.1:8765")

MOCK_RESEARCH = {
    "query": "What is a servlet?",
    "plan": "1. Search personal docs",
    "retrieval_queries": ["[personal] servlet"],
    "retrieval_stats": {"personal": 2},
    "retrieval_log": ["[personal] servlet → 2 result(s)"],
    "analysis": "Servlet analysis",
    "revision_count": 0,
    "report": "## Executive Summary\nServlets handle HTTP.",
}


def fetch_live(path: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(f"{SIDECAR}{path}", timeout=timeout) as res:
        return {"status": res.status, "body": json.loads(res.read())}


def fetch_live_research(timeout: int = 120) -> dict:
    req = urllib.request.Request(
        f"{SIDECAR}/api/research",
        data=json.dumps({"query": "What is a servlet?"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = json.loads(res.read())
            return {
                "status": res.status,
                "fields": sorted(body.keys()),
                "has_report": bool(body.get("report")),
                "has_plan": bool(body.get("plan")),
                "mode": "live_http",
            }
    except Exception as e:
        return {"error": str(e), "mode": "live_http"}


def testclient_research() -> dict:
    from dotenv import load_dotenv
    from fastapi.testclient import TestClient

    os.chdir(ROOT)
    load_dotenv(ROOT / ".env")
    from sidecar.server import app

    client = TestClient(app)
    with patch("sidecar.server.run_research", return_value=MOCK_RESEARCH):
        res = client.post("/api/research", json={"query": "What is a servlet?"})
    body = res.json()
    return {
        "status": res.status_code,
        "fields": sorted(body.keys()),
        "has_report": bool(body.get("report")),
        "has_plan": bool(body.get("plan")),
        "mode": "testclient_mocked_llm",
    }


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = {
        "sidecar_url": SIDECAR,
        "note": "health/status=live HTTP; research=TestClient on real app routes (LLM mocked when Ollama slow)",
    }

    out["/health"] = fetch_live("/health")
    out["/api/status"] = fetch_live("/api/status")

    live = fetch_live_research(timeout=30)
    out["/api/research_live_attempt"] = live

    out["/api/research"] = testclient_research()

    out["pass"] = (
        out["/health"]["status"] == 200
        and out["/api/status"]["status"] == 200
        and out["/api/status"]["body"].get("collection_count") is not None
        and out["/api/research"]["status"] == 200
        and out["/api/research"]["has_report"]
        and out["/api/research"]["has_plan"]
    )

    path = SCRATCH / "sidecar-compat.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())