"""Hypothesis property tests for Pydantic models."""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.models import (
    AuditEntry,
    EscalationReason,
    EscalationRequest,
    EscalationResponse,
    EscalationTier,
    MemoryEntry,
    Plan,
    PlanStep,
    RiskLevel,
    StepStatus,
    Task,
    TaskStatus,
    ToolResult,
    UserRequest,
)

_TEXT = st.text(min_size=1, max_size=200)


@given(text=_TEXT)
@settings(max_examples=20)
def test_user_request_roundtrip(text: str) -> None:
    """UserRequest must survive JSON round-trip serialisation."""
    req = UserRequest(text=text)
    restored = UserRequest.model_validate_json(req.model_dump_json())
    assert restored.id == req.id
    assert restored.text == req.text


@given(text=_TEXT)
@settings(max_examples=20)
def test_tool_result_roundtrip(text: str) -> None:
    """ToolResult must survive JSON round-trip serialisation."""
    tr = ToolResult(success=True, output=text)
    restored = ToolResult.model_validate_json(tr.model_dump_json())
    assert restored.success == tr.success
    assert restored.output == tr.output


@given(text=_TEXT)
@settings(max_examples=20)
def test_plan_step_roundtrip(text: str) -> None:
    """PlanStep must survive JSON round-trip serialisation."""
    step = PlanStep(tool_name=text, description="test step")
    restored = PlanStep.model_validate_json(step.model_dump_json())
    assert restored.tool_name == step.tool_name


@given(text=_TEXT)
@settings(max_examples=20)
def test_memory_entry_roundtrip(text: str) -> None:
    """MemoryEntry must survive JSON round-trip serialisation."""
    entry = MemoryEntry(content=text, tags=["a", "b"])
    restored = MemoryEntry.model_validate_json(entry.model_dump_json())
    assert restored.content == entry.content
    assert restored.tags == entry.tags


def test_audit_entry_is_frozen() -> None:
    """AuditEntry must be immutable (frozen=True)."""
    entry = AuditEntry(task_id="t1", event="test")
    with pytest.raises(Exception):
        entry.event = "changed"  # type: ignore[misc]


def test_user_request_is_frozen() -> None:
    """UserRequest must be immutable (frozen=True)."""
    req = UserRequest(text="hello")
    with pytest.raises(Exception):
        req.text = "changed"  # type: ignore[misc]


def test_task_status_enum_values() -> None:
    """All TaskStatus values must be valid strings."""
    for status in TaskStatus:
        assert isinstance(status.value, str)


def test_risk_level_enum_values() -> None:
    """All RiskLevel values must be valid strings."""
    for level in RiskLevel:
        assert isinstance(level.value, str)
