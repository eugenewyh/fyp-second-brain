from __future__ import annotations

from .state import (
    Acquiring,
    EngineState,
    Failed,
    NotInstalled,
    Ready,
    Starting,
    Unsupported,
)


def _explain(state: EngineState) -> str:
    if isinstance(state, Unsupported):
        return f"local engine unsupported ({state.reason}): {state.detail}"
    if isinstance(state, NotInstalled):
        return f"local engine model {state.model.id} is not installed"
    if isinstance(state, Acquiring):
        return f"local engine is acquiring {state.model.id} ({state.step})"
    if isinstance(state, Starting):
        return f"local engine is starting {state.model.id}"
    if isinstance(state, Ready):
        return f"local engine is ready ({state.model.id})"
    if isinstance(state, Failed):
        return f"local engine failed at {state.stage}: {state.message}"
    return "local engine is not ready"


class LocalEngineNotReady(ValueError):
    """Raised by get_llm when the active provider is local and state is not Ready."""

    def __init__(self, state: EngineState) -> None:
        self.state = state
        super().__init__(_explain(state))
