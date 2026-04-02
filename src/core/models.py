"""Core Pydantic v2 data models for Chief Executive Agent."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware).

    Returns:
        Current UTC datetime with timezone info.
    """
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    """Lifecycle states for a Task."""

    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class RiskLevel(str, Enum):
    """Risk classification for tools and actions."""

    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"


class StepStatus(str, Enum):
    """Execution state for a single plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EscalationTier(int, Enum):
    """Escalation tier indicating which external helper to invoke."""

    TIER1_VSCODE = 1
    TIER2_CLAUDE = 2
    TIER3_BROWSER = 3


class EscalationReason(str, Enum):
    """Reason that triggered escalation."""

    MAX_RETRIES = "max_retries"
    HIGH_RISK = "high_risk"
    PARSE_ERROR = "parse_error"
    USER_REQUEST = "user_request"
    CIRCUIT_OPEN = "circuit_open"


class UserRequest(BaseModel):
    """Immutable representation of the user's original request.

    Args:
        id: Unique identifier.
        text: Raw text entered by the user.
        created_at: UTC timestamp of request creation.

    Returns:
        UserRequest instance.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    created_at: datetime = Field(default_factory=_utcnow)


class PlanStep(BaseModel):
    """A single executable step within a plan.

    Args:
        id: Step identifier (sequential index as string).
        tool_name: Name of the tool to invoke.
        args: Keyword arguments for the tool.
        description: Human-readable description of the step.
        status: Current execution status.
        result: Tool result after execution (None until executed).

    Returns:
        PlanStep instance.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result: ToolResult | None = None


class Plan(BaseModel):
    """Execution plan produced by the planner.

    Args:
        id: Unique plan identifier.
        request_id: ID of the originating UserRequest.
        steps: Ordered list of plan steps.
        reasoning: Planner's reasoning string.
        confidence: Planner confidence score (0–1).

    Returns:
        Plan instance.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    steps: list[PlanStep] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0


class ToolResult(BaseModel):
    """Result returned by every tool execution.

    Args:
        success: Whether the tool call succeeded.
        output: String output from the tool.
        error: Error message if success is False.

    Returns:
        ToolResult instance.
    """

    success: bool
    output: str = ""
    error: str = ""


class EscalationRequest(BaseModel):
    """Request sent to an escalation tier.

    Args:
        id: Unique escalation request ID.
        task_id: ID of the task being escalated.
        step_id: ID of the failing step.
        tier: Target escalation tier.
        reason: Why escalation was triggered.
        context: Additional context string.
        created_at: UTC timestamp.

    Returns:
        EscalationRequest instance.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    step_id: str
    tier: EscalationTier
    reason: EscalationReason
    context: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class EscalationResponse(BaseModel):
    """Response received from an escalation tier.

    Args:
        request_id: ID of the originating EscalationRequest.
        solution: Proposed fix or guidance from the escalation tier.
        confidence: Confidence score of the solution (0–1).
        tier: Tier that produced the response.

    Returns:
        EscalationResponse instance.
    """

    request_id: str
    solution: str
    confidence: float
    tier: EscalationTier


class MemoryEntry(BaseModel):
    """A single entry stored in the memory subsystem.

    Args:
        id: Unique entry ID.
        content: Text content.
        embedding_id: ID in the vector store (optional).
        created_at: UTC timestamp.
        tags: Optional list of tags for filtering.

    Returns:
        MemoryEntry instance.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding_id: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    tags: list[str] = Field(default_factory=list)


class Task(BaseModel):
    """Top-level container for a user task lifecycle.

    Args:
        id: Unique task ID.
        request: The originating user request.
        plan: The execution plan (None until planning completes).
        status: Current task lifecycle status.
        created_at: UTC timestamp of task creation.
        updated_at: UTC timestamp of last update.
        error: Error message if the task failed.

    Returns:
        Task instance.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request: UserRequest
    plan: Plan | None = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    error: str = ""


class AuditEntry(BaseModel):
    """An immutable audit log record.

    Args:
        id: Unique entry ID.
        task_id: Associated task ID.
        step_id: Associated step ID (empty if task-level).
        event: Short event name (e.g. 'tool_executed').
        details: Free-form detail string.
        created_at: UTC timestamp.

    Returns:
        AuditEntry instance.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    step_id: str = ""
    event: str
    details: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
