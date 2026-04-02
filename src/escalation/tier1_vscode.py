"""Tier 1 escalation – VS Code / Cline mock implementation."""
from __future__ import annotations

from src.core.models import EscalationRequest, EscalationResponse, EscalationTier
from src.utils.logging import json_log


async def run(request: EscalationRequest) -> EscalationResponse:
    """Invoke Tier-1 (VS Code / Cline) escalation.

    This is a mock implementation that returns a static payload.
    The real Cline integration will replace this function.

    Args:
        request: The EscalationRequest describing the failure.

    Returns:
        EscalationResponse with a mock solution payload.
    """
    json_log(
        "escalation_tier1_invoked",
        task_id=request.task_id,
        step_id=request.step_id,
        reason=request.reason.value,
    )
    # Mock payload – replace with real Cline CLI call
    return EscalationResponse(
        request_id=request.id,
        solution='{"action": "retry", "patch": "fixed code", "notes": "Tier-1 mock fix"}',
        confidence=0.9,
        tier=EscalationTier.TIER1_VSCODE,
    )


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
