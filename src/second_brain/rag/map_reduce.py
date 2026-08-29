"""Map-reduce synthesis for comprehensive Ask when one source exceeds budget."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.config import (
    DEEP_ASK_MAP_REDUCE_CHARS,
    DEEP_ASK_MAP_REDUCE_SECTIONS,
)
from second_brain.ingestion.sections import SectionIndex, SectionSummary
from second_brain.memory.llm import invoke_llm
from second_brain.memory.recall import MemoryContext
from second_brain.rag.prompts import DEEP_CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_MAP_SYSTEM = """You summarize one section of the user's notes for a later merge step.
Use only the provided section text and claim bullets. Be factual and concise.
Write 4–8 sentences in plain language. Do not invent facts."""

_REDUCE_SYSTEM = DEEP_CHAT_SYSTEM_PROMPT


def needs_map_reduce(
    memory: MemoryContext,
    section_index: SectionIndex | None,
    *,
    comprehensive: bool,
) -> bool:
    if not comprehensive or not section_index or not section_index.sections:
        return False
    if len(memory.text or "") >= DEEP_ASK_MAP_REDUCE_CHARS:
        return True
    return len(section_index.sections) >= DEEP_ASK_MAP_REDUCE_SECTIONS


def _claims_for_section(section: SectionSummary, memory_text: str) -> str:
    """Pull claim lines from memory blob that mention section title tokens."""
    title_tokens = {t.lower() for t in section.title.split() if len(t) > 3}
    if not title_tokens:
        return ""
    lines: list[str] = []
    for line in (memory_text or "").splitlines():
        if not line.strip().startswith("- [["):
            continue
        lower = line.lower()
        if any(tok in lower for tok in title_tokens):
            lines.append(line.strip())
    return "\n".join(lines[:8])


def _map_section(
    question: str,
    section: SectionSummary,
    *,
    memory_text: str,
) -> str:
    claims = _claims_for_section(section, memory_text)
    prompt = (
        f"User question: {question}\n\n"
        f"Section {section.order}: {section.title}\n"
        f"Section summary:\n{section.summary}\n\n"
    )
    if claims:
        prompt += f"Related claims:\n{claims}\n\n"
    prompt += "Write a short section summary for the final study guide:"
    response = invoke_llm(
        [SystemMessage(content=_MAP_SYSTEM), HumanMessage(content=prompt)],
        role="fast",
    )
    text = response.content if isinstance(response.content, str) else str(response.content)
    return text.strip()


def map_reduce_explain(
    question: str,
    *,
    section_index: SectionIndex,
    memory: MemoryContext,
    source_label: str,
) -> str:
    """Parallel map per section (sequential calls), then one reduce merge."""
    partials: list[str] = []
    for section in section_index.sections:
        try:
            partial = _map_section(question, section, memory_text=memory.text or "")
        except Exception:
            logger.exception("Map step failed for section %s", section.title)
            partial = section.summary
        if partial:
            partials.append(f"## {section.title}\n{partial}")

    if not partials:
        return ""

    merged_context = "\n\n".join(partials)
    reduce_prompt = (
        f"Pinned source: {source_label}\n\n"
        f"Section drafts from the user's notes:\n{merged_context}\n\n"
        f"User question: {question}\n\n"
        "Merge into one study-guide answer: short outline first, then filled sections "
        "with inline citations where the drafts support them. Use only the drafts above."
    )
    response = invoke_llm(
        [SystemMessage(content=_REDUCE_SYSTEM), HumanMessage(content=reduce_prompt)],
        role="main",
    )
    return response.content if isinstance(response.content, str) else str(response.content)
