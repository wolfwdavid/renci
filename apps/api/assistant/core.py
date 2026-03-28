"""Assistant engine stub — future conversational layer.

The assistant module will handle:
- Multi-turn conversation with memory
- Proactive suggestions
- Contextual help and explanations

For now, all messages route through the agent engine.
The interface is defined here so the router can switch modes cleanly.
"""


async def handle_conversation(message, owner: dict, business: dict) -> str:
    """Handle a conversational message. Stub for future implementation."""
    raise NotImplementedError("Assistant mode not yet implemented")
