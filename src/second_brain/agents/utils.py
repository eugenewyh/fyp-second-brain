import re

from langchain_core.documents import Document


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
    approved = bool(re.search(r"VERDICT:\s*APPROVED", text, re.IGNORECASE))
    feedback_match = re.search(
        r"FEEDBACK:\s*(.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    feedback = feedback_match.group(1).strip() if feedback_match else text.strip()
    return approved, feedback