"""Escalation manager with in-memory circuit breaker."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.models import (
    AuditEntry,
    EscalationRequest,
    EscalationResponse,
    EscalationTier,
)
from src.safety.audit_log import AuditLog
from src.utils import metrics
from src.utils.logging import json_log


class CircuitBreaker:
    """Simple in-memory circuit breaker per escalation tier.

    States: CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing).

    Args:
        threshold: Number of consecutive failures to open the circuit.
        reset_seconds: Seconds to wait before moving from OPEN to HALF-OPEN.
    """

    def __init__(self, threshold: int = 5, reset_seconds: float = 60.0) -> None:
        self._threshold = threshold
        self._reset_seconds = reset_seconds
        self._failures: dict[EscalationTier, int] = {}
        self._opened_at: dict[EscalationTier, float] = {}

    def is_open(self, tier: EscalationTier) -> bool:
        """Return True if the circuit for the given tier is OPEN.

        Args:
            tier: The escalation tier to check.

        Returns:
            True if the circuit is open (requests should be blocked).
        """
        failures = self._failures.get(tier, 0)
        if failures < self._threshold:
            return False
        opened = self._opened_at.get(tier, 0.0)
        if time.monotonic() - opened >= self._reset_seconds:
            # Reset to half-open
            self._failures[tier] = 0
            return False
        return True

    def record_success(self, tier: EscalationTier) -> None:
        """Record a successful escalation call, resetting the failure counter.

        Args:
            tier: The escalation tier that succeeded.

        Returns:
            None
        """
        self._failures[tier] = 0
        self._opened_at.pop(tier, None)

    def record_failure(self, tier: EscalationTier) -> None:
        """Record a failed escalation call.

        Args:
            tier: The escalation tier that failed.

        Returns:
            None
        """
        self._failures[tier] = self._failures.get(tier, 0) + 1
        if self._failures[tier] >= self._threshold:
            self._opened_at[tier] = time.monotonic()


class EscalationManager:
    """Orchestrate escalation across tiers with circuit-breaker protection.

    Args:
        circuit_breaker: Optional pre-configured CircuitBreaker instance.
    """

    def __init__(self, circuit_breaker: CircuitBreaker | None = None) -> None:
        self._cb = circuit_breaker or CircuitBreaker()

    async def initiate(
        self, request: EscalationRequest, audit: AuditLog
    ) -> EscalationResponse | None:
        """Attempt escalation starting at the requested tier, falling back as needed.

        Args:
            request: The EscalationRequest describing the failure context.
            audit: AuditLog instance for recording escalation events.

        Returns:
            EscalationResponse if a tier succeeded, None if all tiers failed.
        """
        await metrics.inc("escalations_total")
        for tier in (
            EscalationTier.TIER1_VSCODE,
            EscalationTier.TIER2_CLAUDE,
            EscalationTier.TIER3_BROWSER,
        ):
            if tier.value < request.tier.value:
                continue
            if self._cb.is_open(tier):
                json_log("circuit_open", tier=tier.name)
                continue
            try:
                response = await self._call_tier(tier, request)
                self._cb.record_success(tier)
                await audit.log(
                    AuditEntry(
                        task_id=request.task_id,
                        step_id=request.step_id,
                        event="escalation_resolved",
                        details=f"tier={tier.name} solution={response.solution[:100]}",
                    )
                )
                json_log("escalation_resolved", tier=tier.name, task_id=request.task_id)
                return response
            except Exception as exc:
                self._cb.record_failure(tier)
                json_log("escalation_tier_failed", tier=tier.name, error=str(exc))
        return None

    async def _call_tier(
        self, tier: EscalationTier, request: EscalationRequest
    ) -> EscalationResponse:
        """Delegate to the correct tier module.

        Args:
            tier: The tier to call.
            request: The escalation request.

        Returns:
            EscalationResponse from the tier.
        """
        if tier == EscalationTier.TIER1_VSCODE:
            from src.escalation.tier1_vscode import run
        elif tier == EscalationTier.TIER2_CLAUDE:
            from src.escalation.tier2_claude import run  # type: ignore[assignment]
        else:
            from src.escalation.tier3_browser import run  # type: ignore[assignment]
        return await run(request)


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
