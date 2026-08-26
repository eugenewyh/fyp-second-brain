import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.grounding import check_grounding
from second_brain.agents.prompts import VERIFIER_SYSTEM, VERIFIER_USER
from second_brain.agents.utils import (
    docs_from_state,
    grounding_issues_to_critique,
    parse_structured_critique,
)
from second_brain.config import ENABLE_SELF_CRITIQUE, MAX_REVISIONS
from second_brain.memory.llm import invoke_llm
from second_brain.models.critique import (
    CritiqueRevision,
    CritiqueVerdict,
    StructuredCritique,
)
from second_brain.rag.prompts import format_context
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def _analysis_meta(analysis: str) -> tuple[int, str]:
    return len(analysis), (analysis[:200] if analysis else "")


def _revision_entry(
    revision_index: int,
    critique: StructuredCritique,
    analysis: str,
) -> dict:
    char_count, excerpt = _analysis_meta(analysis)
    return CritiqueRevision(
        revision_index=revision_index,
        critique=critique,
        analysis_char_count=char_count,
        analysis_excerpt=excerpt,
    ).to_history_dict()


def _verifier_return(
    *,
    structured: StructuredCritique,
    approved: bool,
    revision_count: int,
    analysis: str,
    bump_revision: bool,
) -> dict:
    """Build node return with free-text + structured + history delta only."""
    new_count = revision_count + 1 if bump_revision else revision_count
    # revision_index: number of verifier passes that requested revise before this one
    # For history, use the count at this pass (0-based on current generation)
    rev_index = revision_count if bump_revision else revision_count
    if approved and structured.source == "forced_max_revisions":
        rev_index = revision_count

    result: dict = {
        "critique": structured.free_text(),
        "critique_approved": approved,
        "critique_structured": structured.model_dump(mode="json"),
        "critique_history": [_revision_entry(rev_index, structured, analysis)],
        "messages": [
            HumanMessage(
                content=f"[Verifier] {'Approved' if approved else 'Revision requested'}"
            )
        ],
    }
    if bump_revision:
        result["revision_count"] = new_count
    return result


def verifier_node(state: GraphState) -> dict:
    query = state["query"]
    analysis = state.get("analysis", "")
    documents = docs_from_state(state.get("retrieved_docs", []))
    revision_count = state.get("revision_count", 0)

    grounded, grounding_issues = check_grounding(analysis, documents)
    if not grounded:
        structured = grounding_issues_to_critique(grounding_issues)
        if not ENABLE_SELF_CRITIQUE:
            # Ablation: record grounding issues but do not loop back to analyst
            structured = StructuredCritique(
                verdict=CritiqueVerdict.approved,
                summary=(
                    "Ablation auto-approve (ENABLE_SELF_CRITIQUE=false). "
                    f"Grounding issues noted: {structured.summary}"
                ),
                issues=list(structured.issues),
                grounding_passed=False,
                source="ablation_auto_approve",
                raw=structured.raw,
            )
            logger.info("Verifier: APPROVED (ablation) after grounding findings")
            return _verifier_return(
                structured=structured,
                approved=True,
                revision_count=revision_count,
                analysis=analysis,
                bump_revision=False,
            )
        logger.info(
            "Verifier: REVISE (grounding) — %d issue(s)", len(grounding_issues)
        )
        return _verifier_return(
            structured=structured,
            approved=False,
            revision_count=revision_count,
            analysis=analysis,
            bump_revision=True,
        )

    context = format_context(documents)

    response = invoke_llm(
        [
            SystemMessage(content=VERIFIER_SYSTEM),
            HumanMessage(
                content=VERIFIER_USER.format(
                    query=query,
                    context=context,
                    analysis=analysis,
                )
            ),
        ],
        temperature=0.1,
        role="fast",
    )
    raw = (
        response.content
        if isinstance(response.content, str)
        else str(response.content)
    )
    structured = parse_structured_critique(raw)
    approved = structured.verdict == CritiqueVerdict.approved

    if not ENABLE_SELF_CRITIQUE and not approved:
        logger.info("Verifier: APPROVED (ablation) — skipping revise loop")
        structured = StructuredCritique(
            verdict=CritiqueVerdict.approved,
            summary=(
                "Ablation auto-approve (ENABLE_SELF_CRITIQUE=false). "
                f"Prior critique: {structured.summary}"
            ),
            issues=list(structured.issues),
            grounding_passed=structured.grounding_passed,
            source="ablation_auto_approve",
            raw=raw,
        )
        return _verifier_return(
            structured=structured,
            approved=True,
            revision_count=revision_count,
            analysis=analysis,
            bump_revision=False,
        )

    if not approved and revision_count >= MAX_REVISIONS:
        logger.info("Verifier: max revisions reached — forcing approval")
        prior_summary = structured.summary
        structured = StructuredCritique(
            verdict=CritiqueVerdict.approved,
            summary=(
                f"Max revisions ({MAX_REVISIONS}) reached. "
                f"Proceeding with best available analysis.\n{prior_summary}"
            ),
            issues=list(structured.issues),
            grounding_passed=structured.grounding_passed,
            source="forced_max_revisions",
            raw=raw,
        )
        approved = True
        return _verifier_return(
            structured=structured,
            approved=True,
            revision_count=revision_count,
            analysis=analysis,
            bump_revision=False,
        )

    logger.info(
        "Verifier: %s",
        "APPROVED" if approved else f"REVISE (attempt {revision_count + 1})",
    )

    return _verifier_return(
        structured=structured,
        approved=approved,
        revision_count=revision_count,
        analysis=analysis,
        bump_revision=not approved,
    )
