import json
import re
from dataclasses import dataclass

from langchain_core.documents import Document

from second_brain.models.critique import (
    CritiqueIssue,
    CritiqueSeverity,
    CritiqueVerdict,
    StructuredCritique,
)


def docs_to_state(documents: list[Document]) -> list[dict]:
    return [
        {"page_content": doc.page_content, "metadata": dict(doc.metadata)}
        for doc in documents
    ]


def docs_from_state(items: list[dict]) -> list[Document]:
    return [
        Document(page_content=item["page_content"], metadata=dict(item["metadata"]))
        for item in items
    ]


@dataclass
class RetrievalQuery:
    source: str
    query: str


def _clean_query_text(query: str) -> str:
    quoted = re.search(r'"([^"]+)"', query)
    if quoted:
        return quoted.group(1).strip()
    if ":" in query:
        return query.rsplit(":", 1)[-1].strip()
    return query.strip()


def parse_retrieval_query(line: str) -> RetrievalQuery:
    stripped = line.strip()
    bracket_match = re.match(r"\[(personal|web|arxiv)\]\s*(.+)", stripped, re.IGNORECASE)
    if bracket_match:
        return RetrievalQuery(
            source=bracket_match.group(1).lower(),
            query=_clean_query_text(bracket_match.group(2)),
        )
    colon_match = re.match(r"(personal|web|arxiv):\s*(.+)", stripped, re.IGNORECASE)
    if colon_match:
        return RetrievalQuery(
            source=colon_match.group(1).lower(),
            query=_clean_query_text(colon_match.group(2)),
        )
    return RetrievalQuery(source="personal", query=_clean_query_text(stripped))


def parse_planner_output(text: str) -> tuple[str, list[str]]:
    plan_match = re.search(
        r"RESEARCH_PLAN:\s*(.*?)(?=SEARCH_QUERIES:|$)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    queries_match = re.search(
        r"SEARCH_QUERIES:\s*(.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    plan = plan_match.group(1).strip() if plan_match else text.strip()
    queries: list[str] = []

    if queries_match:
        block = queries_match.group(1).strip()
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[-*•]\s+", "", line)
            line = re.sub(r"^\d+[.)]\s*", "", line)
            if line:
                queries.append(line)

    return plan, queries


def parse_verifier_output(text: str) -> tuple[bool, str]:
    """Legacy regex parser — VERDICT + FEEDBACK free-text."""
    approved = bool(re.search(r"VERDICT:\s*APPROVED", text, re.IGNORECASE))
    feedback_match = re.search(
        r"FEEDBACK:\s*(.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    feedback = feedback_match.group(1).strip() if feedback_match else text.strip()
    return approved, feedback


def _extract_json_object(text: str) -> dict | None:
    """Try to parse a JSON object from raw LLM text (fenced or bare)."""
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            data = json.loads(fence.group(1))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(stripped[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def structured_critique_from_fallback(raw: str) -> StructuredCritique:
    """Build StructuredCritique from VERDICT/FEEDBACK regex path."""
    approved, feedback = parse_verifier_output(raw)
    if approved:
        return StructuredCritique(
            verdict=CritiqueVerdict.approved,
            summary=feedback,
            issues=[],
            grounding_passed=True,
            source="llm",
            raw=raw,
        )
    return StructuredCritique(
        verdict=CritiqueVerdict.revise,
        summary=feedback,
        issues=[
            CritiqueIssue(
                code="other",
                severity=CritiqueSeverity.major,
                message=feedback[:500],
                citation_indices=[],
            )
        ],
        grounding_passed=True,
        source="llm",
        raw=raw,
    )


def parse_structured_critique(raw: str) -> StructuredCritique:
    """Parse LLM verifier output: prefer JSON, fall back to VERDICT/FEEDBACK."""
    data = _extract_json_object(raw)
    if data is not None:
        try:
            verdict_raw = str(data.get("verdict", "revise")).lower().strip()
            if verdict_raw in {"approved", "approve", "ok", "pass"}:
                data["verdict"] = CritiqueVerdict.approved.value
            else:
                data["verdict"] = CritiqueVerdict.revise.value
            data.setdefault("grounding_passed", True)
            data.setdefault("source", "llm")
            data["raw"] = raw
            issues_in = data.get("issues") or []
            coerced: list[dict] = []
            for item in issues_in:
                if isinstance(item, dict):
                    coerced.append(item)
                elif isinstance(item, str):
                    coerced.append(
                        {
                            "code": "other",
                            "severity": "major",
                            "message": item,
                        }
                    )
            data["issues"] = coerced
            if not data.get("summary") and coerced:
                data["summary"] = "\n".join(
                    f"- {i.get('message', '')}" for i in coerced if i.get("message")
                )
            return StructuredCritique.model_validate(data)
        except Exception:
            pass
    return structured_critique_from_fallback(raw)


def grounding_issues_to_critique(issue_strings: list[str]) -> StructuredCritique:
    """Map rule-based grounding failure strings to StructuredCritique."""
    issues: list[CritiqueIssue] = []
    for text in issue_strings:
        lower = text.lower()
        indices: list[int] = []

        if "invalid citation" in lower:
            code = "invalid_citation"
            severity = CritiqueSeverity.blocking
            m = re.search(r"indices\s*\[([^\]]+)\]", text, re.I)
            if m:
                indices = [
                    int(x.strip())
                    for x in m.group(1).split(",")
                    if x.strip().lstrip("-").isdigit()
                ]
        elif "academic" in lower:
            code = "academic_mislabel"
            severity = CritiqueSeverity.major
            indices = [int(m) for m in re.findall(r"\[(\d+)\]", text)]
        else:
            code = "other"
            severity = CritiqueSeverity.major
            indices = [int(m) for m in re.findall(r"\[(\d+)\]", text)]

        issues.append(
            CritiqueIssue(
                code=code,
                severity=severity,
                message=text,
                citation_indices=indices,
            )
        )

    summary = "\n".join(f"- {i.message}" for i in issues)
    return StructuredCritique(
        verdict=CritiqueVerdict.revise,
        summary=summary,
        issues=issues,
        grounding_passed=False,
        source="grounding",
        raw="\n".join(issue_strings),
    )
