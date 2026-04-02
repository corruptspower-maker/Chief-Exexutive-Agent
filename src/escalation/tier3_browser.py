"""Tier 3 escalation – Browser automation mock implementation."""
from __future__ import annotations

import asyncio

from src.core.models import EscalationRequest, EscalationResponse, EscalationTier
from src.utils.logging import json_log


async def run(request: EscalationRequest) -> EscalationResponse:
    """Invoke Tier-3 (browser/ChatGPT) escalation.

    This is a mock implementation with a simulated Playwright latency.
    The real BrowserTool integration will replace this function.

    Args:
        request: The EscalationRequest describing the failure.

    Returns:
        EscalationResponse with a mock solution payload.
    """
    json_log(
        "escalation_tier3_invoked",
        task_id=request.task_id,
        step_id=request.step_id,
        reason=request.reason.value,
    )
    # Simulate Playwright browser latency
    await asyncio.sleep(5)
    # Mock payload – replace with real BrowserTool call
    return EscalationResponse(
        request_id=request.id,
        solution='{"action": "manual", "notes": "Tier-3 browser mock fix", "confidence": 0.7}',
        confidence=0.7,
        tier=EscalationTier.TIER3_BROWSER,
    )


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
