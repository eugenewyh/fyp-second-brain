import re
from dataclasses import dataclass

_SOURCE_LABELS = {
    "personal": "Personal",
    "web": "Web",
    "arxiv": "arXiv",
    "mcp": "Notion",
}

_CITE_RE = re.compile(r"\[(\d+)\]")


def format_bibliography(documents: list) -> str:
    if not documents:
        return "_No sources retrieved._"

    lines = []
    for index, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "unknown")
        source_type = doc.metadata.get("source_type", "personal")
        type_label = _SOURCE_LABELS.get(source_type, "Source")
        page = doc.metadata.get("page", -1)
        url = doc.metadata.get("source_path", "")

        if source_type == "personal" and page >= 0:
            lines.append(f"[{index}] {type_label} — {source}, p.{page + 1}")
        elif url and source_type in {"web", "arxiv", "mcp"}:
            lines.append(f"[{index}] {type_label} — {source} ({url})")
        else:
            lines.append(f"[{index}] {type_label} — {source}")

    return "\n".join(lines)


def strip_sources_section(report: str) -> str:
    match = re.search(r"\n##\s*Sources\s*\n", report, re.IGNORECASE)
    if match:
        return report[: match.start()].rstrip()
    return report.rstrip()


@dataclass
class CitationCheckResult:
    ok: bool
    issues: list[str]
    cited_indices: list[int]
    invalid_indices: list[int]
    unused_indices: list[int]


def check_report_citations(report: str, document_count: int) -> CitationCheckResult:
    """Validate inline [n] citations against retrieved document count."""
    body = strip_sources_section(report or "")
    cited = sorted({int(m) for m in _CITE_RE.findall(body)})
    invalid = [i for i in cited if i < 1 or i > document_count]
    issues: list[str] = []
    if document_count > 0 and not cited and len(body) > 200:
        issues.append("Report body has no inline citations despite available sources.")
    if invalid:
        issues.append(
            f"Out-of-range citation indices {invalid} "
            f"(valid range is [1]–[{document_count}])."
        )
    unused = [i for i in range(1, document_count + 1) if i not in cited]
    # Unused sources are informational only (not a hard failure)
    return CitationCheckResult(
        ok=len(issues) == 0,
        issues=issues,
        cited_indices=cited,
        invalid_indices=invalid,
        unused_indices=unused,
    )


def scrub_invalid_citations(report: str, document_count: int) -> str:
    """Remove out-of-range [n] markers from the report body (keep Sources intact)."""
    if document_count <= 0:
        return report

    def repl(match: re.Match[str]) -> str:
        n = int(match.group(1))
        if 1 <= n <= document_count:
            return match.group(0)
        return ""

    # Only scrub body before ## Sources
    sources_match = re.search(r"\n##\s*Sources\s*\n", report or "", re.IGNORECASE)
    if sources_match:
        body = report[: sources_match.start()]
        tail = report[sources_match.start() :]
        return _CITE_RE.sub(repl, body) + tail
    return _CITE_RE.sub(repl, report or "")