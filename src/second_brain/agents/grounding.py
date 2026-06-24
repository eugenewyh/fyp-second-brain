import re

from langchain_core.documents import Document

_ACADEMIC_TERMS = re.compile(
    r"\b(academic\s+paper|arxiv|journal|et\s+al\.|peer[- ]reviewed|"
    r"published\s+study|research\s+paper|scholarly)\b",
    re.IGNORECASE,
)


def extract_citation_indices(text: str) -> set[int]:
    return {int(match) for match in re.findall(r"\[(\d+)\]", text)}


def check_grounding(analysis: str, documents: list[Document]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    doc_count = len(documents)
    cited = extract_citation_indices(analysis)

    invalid = sorted(i for i in cited if i < 1 or i > doc_count)
    if invalid:
        issues.append(
            f"Invalid citation indices {invalid}. Only [1]–[{doc_count}] exist in retrieved sources."
        )

    has_arxiv = any(doc.metadata.get("source_type") == "arxiv" for doc in documents)

    if _ACADEMIC_TERMS.search(analysis) and not has_arxiv:
        issues.append(
            "Analysis mentions academic papers but no arXiv sources were retrieved. "
            "Remove academic paper claims or note the absence of academic sources in gaps."
        )

    for index in cited:
        if not (1 <= index <= doc_count):
            continue
        doc = documents[index - 1]
        source_type = doc.metadata.get("source_type", "personal")
        if source_type in {"web", "personal"}:
            for match in re.finditer(rf".{{0,120}}\[{index}\].{{0,120}}", analysis, re.IGNORECASE):
                if _ACADEMIC_TERMS.search(match.group(0)):
                    source_name = doc.metadata.get("source", "unknown")
                    issues.append(
                        f"Citation [{index}] is a {source_type} source ({source_name}) "
                        f"but is described using academic language. Use the correct source type."
                    )
                    break

    return len(issues) == 0, issues