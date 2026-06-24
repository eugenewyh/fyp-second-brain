import re

_SOURCE_LABELS = {
    "personal": "Personal",
    "web": "Web",
    "arxiv": "arXiv",
}


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
        elif url and source_type in {"web", "arxiv"}:
            lines.append(f"[{index}] {type_label} — {source} ({url})")
        else:
            lines.append(f"[{index}] {type_label} — {source}")

    return "\n".join(lines)


def strip_sources_section(report: str) -> str:
    match = re.search(r"\n##\s*Sources\s*\n", report, re.IGNORECASE)
    if match:
        return report[: match.start()].rstrip()
    return report.rstrip()