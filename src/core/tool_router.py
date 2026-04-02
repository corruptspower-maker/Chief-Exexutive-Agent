"""Tool dispatch router with tenacity retry logic."""
from __future__ import annotations

import asyncio

import tenacity

from src.core.models import PlanStep, ToolResult
from src.tools.registry import TOOL_REGISTRY
from src.utils import metrics


class ToolRouter:
    """Route a PlanStep to the appropriate tool and execute it.

    Wraps every dispatch call in a tenacity retry decorator (3 retries,
    exponential backoff with a 1-second base).
    """

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        stop=tenacity.stop_after_attempt(3),
        reraise=True,
    )
    async def dispatch(self, step: PlanStep) -> ToolResult:
        """Look up the tool for the step and execute it.

        Args:
            step: The PlanStep to execute, containing tool_name and args.

        Returns:
            ToolResult from the tool execution.

        Raises:
            KeyError: If the tool is not found in the registry.
        """
        tool_cls = TOOL_REGISTRY.get(step.tool_name)
        if tool_cls is None:
            return ToolResult(success=False, error=f"Unknown tool '{step.tool_name}'")
        tool = tool_cls()
        valid, msg = await tool.validate(**step.args)
        if not valid:
            return ToolResult(success=False, error=msg)
        result = await tool.execute(**step.args)
        await metrics.inc(f"tool_executions_{step.tool_name}")
        return result


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
