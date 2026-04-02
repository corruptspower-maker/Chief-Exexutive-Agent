"""Core async executive state machine for Chief Executive Agent."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.core.models import (
    AuditEntry,
    EscalationReason,
    EscalationRequest,
    EscalationTier,
    PlanStep,
    StepStatus,
    Task,
    TaskStatus,
    UserRequest,
)
from src.core.planner import LocalPlanner
from src.core.tool_router import ToolRouter
from src.escalation.manager import EscalationManager
from src.safety.audit_log import AuditLog
from src.safety.classifier import classify
from src.safety.confirmation import ConfirmationProtocol
from src.safety.limiter import allow as rate_allow
from src.core.models import RiskLevel
from src.utils import metrics
from src.utils.logging import json_log


class ExecutiveAgent:
    """Async state machine that orchestrates planning, execution, and escalation.

    Args:
        planner: LocalPlanner instance for generating plans.
        router: ToolRouter for dispatching steps.
        escalation: EscalationManager for handling failures.
        audit: AuditLog for recording events.
        safety: ConfirmationProtocol for high-risk confirmations.
    """

    def __init__(
        self,
        planner: LocalPlanner,
        router: ToolRouter,
        escalation: EscalationManager,
        audit: AuditLog,
        safety: ConfirmationProtocol,
    ) -> None:
        self._planner = planner
        self._router = router
        self._escalation = escalation
        self._audit = audit
        self._safety = safety
        self._llm_semaphore = asyncio.Semaphore(1)

    async def process(self, text: str) -> Task:
        """Process a raw user text input through the full task lifecycle.

        Args:
            text: Raw text entered by the user.

        Returns:
            The completed (or failed) Task after all steps have been attempted.
        """
        request = UserRequest(text=text)
        task = Task(request=request, status=TaskStatus.PLANNING)
        await metrics.inc("tasks_total")
        await self._audit.log(
            AuditEntry(task_id=task.id, event="task_started", details=text)
        )
        json_log("task_started", task_id=task.id, text=text)
        try:
            plan = await self._planner.generate(request)
            task.plan = plan
            task.status = TaskStatus.RUNNING
            await self._run_plan(task)
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            await self._audit.log(
                AuditEntry(task_id=task.id, event="task_failed", details=str(exc))
            )
            json_log("task_failed", task_id=task.id, error=str(exc))
        finally:
            task.updated_at = datetime.now(timezone.utc)
        return task

    async def _run_plan(self, task: Task) -> None:
        """Execute every step in the task's plan sequentially.

        Args:
            task: The Task containing the plan to execute.

        Returns:
            None
        """
        if task.plan is None:
            raise RuntimeError("No plan to execute.")
        for step in task.plan.steps:
            step.status = StepStatus.RUNNING
            await self._execute_step(task, step)
            if step.status == StepStatus.FAILED:
                task.status = TaskStatus.ESCALATED
                return
        task.status = TaskStatus.COMPLETED

    async def _execute_step(self, task: Task, step: PlanStep) -> None:
        """Execute a single plan step with safety checks and audit logging.

        Args:
            task: Parent task context.
            step: The PlanStep to execute.

        Returns:
            None
        """
        risk = classify(step.tool_name, step.args)
        if not await rate_allow(step.tool_name):
            step.status = StepStatus.FAILED
            step.result = None
            await self._audit.log(
                AuditEntry(
                    task_id=task.id,
                    step_id=step.id,
                    event="rate_limited",
                    details=step.tool_name,
                )
            )
            return
        if risk in (RiskLevel.DANGEROUS, RiskLevel.MODERATE):
            confirmed = await self._safety.ask(
                f"Step '{step.description or step.tool_name}' is classified as {risk.value.upper()}.\n"
                f"Args: {step.args}"
            )
            if not confirmed:
                step.status = StepStatus.SKIPPED
                await self._audit.log(
                    AuditEntry(
                        task_id=task.id,
                        step_id=step.id,
                        event="step_skipped",
                        details="User declined confirmation.",
                    )
                )
                return
        try:
            result = await self._router.dispatch(step)
            step.result = result
            if result.success:
                step.status = StepStatus.COMPLETED
                await self._audit.log(
                    AuditEntry(
                        task_id=task.id,
                        step_id=step.id,
                        event="step_completed",
                        details=result.output[:200],
                    )
                )
            else:
                step.status = StepStatus.FAILED
                await self._handle_step_failure(task, step, result.error)
        except Exception as exc:
            step.status = StepStatus.FAILED
            await self._handle_step_failure(task, step, str(exc))

    async def _handle_step_failure(self, task: Task, step: PlanStep, error: str) -> None:
        """Log and escalate a failed step.

        Args:
            task: Parent task.
            step: The step that failed.
            error: Error message describing the failure.

        Returns:
            None
        """
        await self._audit.log(
            AuditEntry(
                task_id=task.id,
                step_id=step.id,
                event="step_failed",
                details=error[:500],
            )
        )
        json_log("step_failed", task_id=task.id, step_id=step.id, error=error)
        esc_req = EscalationRequest(
            task_id=task.id,
            step_id=step.id,
            tier=EscalationTier.TIER1_VSCODE,
            reason=EscalationReason.MAX_RETRIES,
            context=error,
        )
        await self._escalation.initiate(esc_req, self._audit)


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
