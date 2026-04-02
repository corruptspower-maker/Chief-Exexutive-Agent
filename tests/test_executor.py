"""Tests for tool execution via the sandbox."""
from __future__ import annotations

import pytest

from src.core.models import PlanStep
from src.core.tool_router import ToolRouter
from src.tools.shell_tool import ShellTool


@pytest.mark.asyncio
async def test_shell_echo_success() -> None:
    """ShellTool should execute 'echo hello' and return success."""
    tool = ShellTool()
    result = await tool.execute(command="echo", args=["hello"])
    assert result.success is True
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_shell_forbidden_command() -> None:
    """ShellTool should refuse a command not in the whitelist."""
    tool = ShellTool()
    result = await tool.execute(command="del", args=[r"C:\Windows\system32\*"])
    assert result.success is False
    assert "whitelist" in result.error.lower()


@pytest.mark.asyncio
async def test_tool_router_dispatch_echo() -> None:
    """ToolRouter should dispatch shell_tool echo and return success."""
    router = ToolRouter()
    step = PlanStep(
        tool_name="shell_tool",
        args={"command": "echo", "args": ["hello"]},
        description="Echo test",
    )
    result = await router.dispatch(step)
    assert result.success is True
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_tool_router_unknown_tool() -> None:
    """ToolRouter should return a failure for an unknown tool name."""
    router = ToolRouter()
    step = PlanStep(tool_name="nonexistent_tool", args={})
    result = await router.dispatch(step)
    assert result.success is False
    assert "Unknown tool" in result.error
