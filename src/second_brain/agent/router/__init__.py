"""Unified local-first routing for Manager Auto mode."""

from second_brain.agent.router.copy import CLARIFY_ASKS, DISPATCH_COPY, REFUSE_MESSAGE
from second_brain.agent.router.decision import RouteDecision
from second_brain.agent.router.local_model import model_loaded, route_job
from second_brain.agent.router.llm_router import llm_choose
from second_brain.agent.router.meta import capability_reply, is_meta_intent
from second_brain.agent.router.recall import RecallSnapshot, recall_snapshot, topic_name
from second_brain.agent.router.turn import route_act, route_turn
from second_brain.agent.router.voice import apply_voice, generate_voice

__all__ = [
    "CLARIFY_ASKS",
    "DISPATCH_COPY",
    "REFUSE_MESSAGE",
    "RecallSnapshot",
    "RouteDecision",
    "apply_voice",
    "capability_reply",
    "generate_voice",
    "is_meta_intent",
    "llm_choose",
    "model_loaded",
    "recall_snapshot",
    "route_act",
    "route_job",
    "route_turn",
    "topic_name",
]
