"""User-facing copy for routing outcomes."""

REFUSE_MESSAGE = (
    "I don't have notes on this topic yet. Teach something here first — "
    "then Ask from what you saved."
)

CLARIFY_ASKS = (
    "What are you trying to get done?",
    "Your notes only, or should I look up papers too?",
)

DISPATCH_COPY = {
    "file": "Filing that into memory.",
    "answer": "Checking your notes.",
    "research": "I'll look this up.",
    "refuse": REFUSE_MESSAGE,
}
