"""Tests for Tier-1 escalation invocation."""
from __future__ import annotations

import pytest

from src.core.models import EscalationReason, EscalationRequest, EscalationTier
from src.escalation.manager import CircuitBreaker, EscalationManager
from src.escalation import tier1_vscode
from src.safety.audit_log import AuditLog


@pytest.mark.asyncio
async def test_tier1_returns_response() -> None:
    """tier1_vscode.run should return an EscalationResponse with confidence > 0."""
    request = EscalationRequest(
        task_id="task-1",
        step_id="step-1",
        tier=EscalationTier.TIER1_VSCODE,
        reason=EscalationReason.MAX_RETRIES,
        context="tool failed",
    )
    response = await tier1_vscode.run(request)
    assert response.tier == EscalationTier.TIER1_VSCODE
    assert response.confidence > 0
    assert response.solution


@pytest.mark.asyncio
async def test_manager_invokes_tier1_on_failure() -> None:
    """EscalationManager.initiate should call Tier-1 and log the escalation."""
    manager = EscalationManager()
    audit = AuditLog()
    request = EscalationRequest(
        task_id="task-2",
        step_id="step-2",
        tier=EscalationTier.TIER1_VSCODE,
        reason=EscalationReason.MAX_RETRIES,
        context="repeated failure",
    )
    response = await manager.initiate(request, audit)
    assert response is not None
    assert response.tier == EscalationTier.TIER1_VSCODE

    # Verify the escalation was logged
    entries = await audit.query("task-2")
    events = [e.event for e in entries]
    assert "escalation_resolved" in events


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold() -> None:
    """CircuitBreaker should open after recording threshold failures."""
    cb = CircuitBreaker(threshold=2, reset_seconds=60.0)
    tier = EscalationTier.TIER1_VSCODE
    assert not cb.is_open(tier)
    cb.record_failure(tier)
    assert not cb.is_open(tier)
    cb.record_failure(tier)
    assert cb.is_open(tier)
