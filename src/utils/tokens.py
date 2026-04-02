"""Token-window enforcement for LLM prompts."""
from __future__ import annotations


def _count_tokens(text: str) -> int:
    """Estimate token count using whitespace splitting (tiktoken-compatible stub).

    Args:
        text: The text to count tokens for.

    Returns:
        Approximate number of tokens.
    """
    return len(text.split())


def enforce_window(
    system: str,
    memory: str,
    convo: str,
    max_tokens: int = 8192,
) -> str:
    """Combine system, memory, and conversation sections within a token budget.

    Prioritises recent conversation content; truncates memory and then system
    sections when the budget is exceeded. Returns the combined prompt string.

    Args:
        system: System-level instruction text.
        memory: Relevant memory context retrieved for the current turn.
        convo: Recent conversation history.
        max_tokens: Maximum total token budget.

    Returns:
        Combined prompt string fitting within max_tokens.
    """
    convo_tokens = _count_tokens(convo)
    memory_tokens = _count_tokens(memory)
    system_tokens = _count_tokens(system)

    # Reserve space for conversation first
    remaining = max_tokens - convo_tokens
    if remaining <= 0:
        # Conversation alone exceeds budget – truncate to latest tokens
        words = convo.split()
        return " ".join(words[-max_tokens:])

    # Allocate memory tokens within remaining budget
    allowed_memory_tokens = min(memory_tokens, remaining // 2)
    remaining -= allowed_memory_tokens

    # Allocate system tokens
    allowed_system_tokens = min(system_tokens, remaining)

    truncated_memory = _truncate_to_tokens(memory, allowed_memory_tokens)
    truncated_system = _truncate_to_tokens(system, allowed_system_tokens)

    parts = [p for p in (truncated_system, truncated_memory, convo) if p]
    return "\n\n".join(parts)


def _truncate_to_tokens(text: str, max_tok: int) -> str:
    """Truncate text to at most max_tok whitespace-split tokens.

    Args:
        text: Input text to truncate.
        max_tok: Maximum allowed tokens.

    Returns:
        Truncated text string.
    """
    if max_tok <= 0:
        return ""
    words = text.split()
    return " ".join(words[:max_tok])


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
