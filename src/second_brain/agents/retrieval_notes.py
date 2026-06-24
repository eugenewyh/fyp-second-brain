def build_retrieval_notes(retrieval_stats: dict[str, int], retrieval_log: list[str]) -> str:
    notes: list[str] = []
    attempted_arxiv = any(entry.lower().startswith("[arxiv]") for entry in retrieval_log)

    if attempted_arxiv and retrieval_stats.get("arxiv", 0) == 0:
        notes.append(
            "RETRIEVAL NOTE: arXiv returned no relevant papers for this topic. "
            "Do not invent academic paper claims. Mention this gap explicitly."
        )

    attempted_web = any(entry.lower().startswith("[web]") for entry in retrieval_log)
    if attempted_web and retrieval_stats.get("web", 0) == 0:
        notes.append(
            "RETRIEVAL NOTE: Web search returned no results. "
            "Rely only on personal sources and note limited external coverage."
        )

    if not notes:
        return ""

    return "\n".join(notes) + "\n\n"