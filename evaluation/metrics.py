import re
from dataclasses import dataclass, field
from typing import Any


_REFUSAL = re.compile(
    r"(do not contain|does not contain|don't contain|not (in|found in) (my |the )?(notes|documents|library|vault)|"
    r"no information|not covered|nothing in (my |the )?(notes|documents)|"
    r"cannot (find|answer)|don't know|do not know|not mentioned)",
    re.I,
)


@dataclass
class QueryMetrics:
    query_id: str
    category: str
    mode: str
    success: bool
    latency_seconds: float
    error: str = ""
    answer_length: int = 0
    has_citations: bool = False
    citation_count: int = 0
    source_count: int = 0
    personal_sources: int = 0
    web_sources: int = 0
    arxiv_sources: int = 0
    revision_count: int = 0
    has_gaps_section: bool = False
    mentions_no_arxiv: bool = False
    mentions_gap: bool = False
    gold_hit: bool | None = None
    honest_gap: bool | None = None
    invented: bool = False


def count_citations(text: str) -> int:
    return len(set(re.findall(r"\[(\d+)\]", text)))


def has_section(text: str, section: str) -> bool:
    return bool(re.search(rf"##\s*{re.escape(section)}", text, re.IGNORECASE))


def _norm(text: str) -> str:
    return (text or "").lower()


def score_expect(text: str, expect: dict[str, Any] | None) -> tuple[bool | None, bool | None, bool]:
    """Return (gold_hit, honest_gap, invented)."""
    if not expect:
        return None, None, False
    body = _norm(text)
    kind = (expect.get("kind") or "").strip().lower()
    all_of = [s.lower() for s in (expect.get("all_of") or []) if s]
    any_of = [s.lower() for s in (expect.get("any_of") or []) if s]
    none_of = [s.lower() for s in (expect.get("none_of") or []) if s]

    invented = any(s in body for s in none_of)
    gold_ok = True
    if all_of:
        gold_ok = gold_ok and all(s in body for s in all_of)
    if any_of:
        gold_ok = gold_ok and any(s in body for s in any_of)

    if kind == "gap":
        refused = bool(_REFUSAL.search(text or "")) or ("not contain" in body)
        honest = refused and not invented
        return gold_ok if any_of or all_of else honest, honest, invented

    return gold_ok, None, invented


def analyze_query_result(
    query_id: str,
    category: str,
    mode: str,
    latency: float,
    success: bool,
    error: str = "",
    answer: str = "",
    sources: list | None = None,
    retrieval_stats: dict | None = None,
    revision_count: int = 0,
    expect: dict[str, Any] | None = None,
) -> QueryMetrics:
    sources = sources or []
    stats = retrieval_stats or {}
    text = answer or ""
    gold_hit, honest_gap, invented = score_expect(text, expect)

    return QueryMetrics(
        query_id=query_id,
        category=category,
        mode=mode,
        success=success,
        latency_seconds=round(latency, 2),
        error=error,
        answer_length=len(text),
        has_citations=bool(re.search(r"\[\d+\]", text)),
        citation_count=count_citations(text),
        source_count=len(sources) if sources else sum(stats.values()),
        personal_sources=stats.get("personal", 0),
        web_sources=stats.get("web", 0),
        arxiv_sources=stats.get("arxiv", 0),
        revision_count=revision_count,
        has_gaps_section=(
            has_section(text, "Identified Gaps")
            or has_section(text, "What's missing")
            or has_section(text, "Whats missing")
        ),
        mentions_no_arxiv=bool(re.search(r"no relevant arxiv|arxiv returned no|no arxiv", text, re.I)),
        mentions_gap=bool(re.search(r"gap|not cover|missing|limited", text, re.I)),
        gold_hit=gold_hit,
        honest_gap=honest_gap,
        invented=invented,
    )


@dataclass
class EvaluationSummary:
    total: int = 0
    completed: int = 0
    failed: int = 0
    avg_latency_seconds: float = 0.0
    citation_rate: float = 0.0
    gaps_section_rate: float = 0.0
    gold_hit_rate: float | None = None
    honest_gap_rate: float | None = None
    invented_rate: float = 0.0
    by_category: dict = field(default_factory=dict)


def summarize(metrics: list[QueryMetrics]) -> EvaluationSummary:
    if not metrics:
        return EvaluationSummary()

    completed = [m for m in metrics if m.success]
    failed = [m for m in metrics if not m.success]

    by_category: dict[str, dict] = {}
    for m in metrics:
        cat = by_category.setdefault(m.category, {"total": 0, "success": 0, "avg_latency": 0.0, "latencies": []})
        cat["total"] += 1
        if m.success:
            cat["success"] += 1
            cat["latencies"].append(m.latency_seconds)

    for cat in by_category.values():
        latencies = cat.pop("latencies", [])
        cat["avg_latency"] = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    golded = [m for m in completed if m.gold_hit is not None]
    gapped = [m for m in completed if m.honest_gap is not None]

    return EvaluationSummary(
        total=len(metrics),
        completed=len(completed),
        failed=len(failed),
        avg_latency_seconds=round(sum(m.latency_seconds for m in completed) / len(completed), 2) if completed else 0.0,
        citation_rate=round(sum(1 for m in completed if m.has_citations) / len(completed), 3) if completed else 0.0,
        gaps_section_rate=round(sum(1 for m in completed if m.has_gaps_section) / len(completed), 3) if completed else 0.0,
        gold_hit_rate=round(sum(1 for m in golded if m.gold_hit) / len(golded), 3) if golded else None,
        honest_gap_rate=round(sum(1 for m in gapped if m.honest_gap) / len(gapped), 3) if gapped else None,
        invented_rate=round(sum(1 for m in completed if m.invented) / len(completed), 3) if completed else 0.0,
        by_category=by_category,
    )
