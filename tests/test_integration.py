"""Full integration test: ExecutiveAgent.process with all tools mocked."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.executive import ExecutiveAgent
from src.core.models import TaskStatus, ToolResult
from src.core.planner import LocalPlanner
from src.core.tool_router import ToolRouter
from src.escalation.manager import EscalationManager
from src.safety.audit_log import AuditLog
from src.safety.confirmation import ConfirmationProtocol


class _AutoConfirmProtocol(ConfirmationProtocol):
    """Confirmation protocol that always returns True (no human interaction)."""

    async def ask(self, user_prompt: str) -> bool:  # noqa: D102
        return True


@pytest.mark.asyncio
async def test_full_flow_completed(mock_lmstudio: AsyncMock) -> None:
    """Full agent flow should reach COMPLETED status with all tools mocked."""
    # Patch ToolRouter.dispatch to always return success
    mock_dispatch = AsyncMock(
        return_value=ToolResult(success=True, output="mocked output")
    )
    with patch.object(ToolRouter, "dispatch", mock_dispatch):
        planner = LocalPlanner()
        router = ToolRouter()
        escalation = EscalationManager()
        audit = AuditLog()
        safety = _AutoConfirmProtocol()
        agent = ExecutiveAgent(planner, router, escalation, audit, safety)

        task = await agent.process("find my insurance pdf and email it")

    assert task.status == TaskStatus.COMPLETED
    assert task.plan is not None
    assert len(task.plan.steps) >= 1


@pytest.mark.asyncio
async def test_full_flow_failed_step_triggers_escalation(
    mock_lmstudio: AsyncMock,
) -> None:
    """A failing tool dispatch should escalate and set status to ESCALATED."""
    mock_dispatch = AsyncMock(
        return_value=ToolResult(success=False, error="deliberate failure")
    )
    with patch.object(ToolRouter, "dispatch", mock_dispatch):
        planner = LocalPlanner()
        router = ToolRouter()
        escalation = EscalationManager()
        audit = AuditLog()
        safety = _AutoConfirmProtocol()
        agent = ExecutiveAgent(planner, router, escalation, audit, safety)

        task = await agent.process("trigger failure scenario")

    assert task.status == TaskStatus.ESCALATED
