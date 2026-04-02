"""Tier 2 escalation – Claude API mock implementation."""
from __future__ import annotations

import asyncio

from src.core.models import EscalationRequest, EscalationResponse, EscalationTier
from src.utils.logging import json_log


async def run(request: EscalationRequest) -> EscalationResponse:
    """Invoke Tier-2 (Claude) escalation.

    This is a mock implementation with a simulated latency.
    The real Claude API integration will replace this function.

    Args:
        request: The EscalationRequest describing the failure.

    Returns:
        EscalationResponse with a mock solution payload.
    """
    json_log(
        "escalation_tier2_invoked",
        task_id=request.task_id,
        step_id=request.step_id,
        reason=request.reason.value,
    )
    # Simulate API latency
    await asyncio.sleep(2)
    # Mock payload – replace with real Claude API call
    return EscalationResponse(
        request_id=request.id,
        solution='{"action": "rewrite", "patch": "claude-rewritten code", "notes": "Tier-2 mock fix"}',
        confidence=0.85,
        tier=EscalationTier.TIER2_CLAUDE,
    )


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
