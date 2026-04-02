"""Tests for LocalPlanner using a mocked LM-Studio client."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.models import UserRequest
from src.core.planner import LocalPlanner


@pytest.mark.asyncio
async def test_generate_returns_plan(mock_lmstudio: AsyncMock) -> None:
    """LocalPlanner.generate should return a Plan with at least one step."""
    planner = LocalPlanner()
    request = UserRequest(text="echo hello")
    plan = await planner.generate(request)
    assert plan.request_id == request.id
    assert len(plan.steps) >= 1
    assert plan.steps[0].tool_name == "shell_tool"


@pytest.mark.asyncio
async def test_generate_raises_on_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """LocalPlanner.generate should raise RuntimeError if LLM returns invalid JSON."""
    bad_response = MagicMock()
    bad_response.status_code = 200
    bad_response.json.return_value = {
        "choices": [{"message": {"content": "not valid json {"}}]
    }
    bad_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=bad_response)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)

    planner = LocalPlanner()
    request = UserRequest(text="bad request")
    with pytest.raises(RuntimeError, match="Planner failed"):
        await planner.generate(request)


@pytest.mark.asyncio
async def test_llm_semaphore_serialises_requests(
    mock_lmstudio: AsyncMock,
) -> None:
    """Concurrent planner calls must be serialised by the semaphore."""
    sem = asyncio.Semaphore(1)
    planner = LocalPlanner(llm_semaphore=sem)
    requests = [UserRequest(text=f"task {i}") for i in range(3)]
    plans = await asyncio.gather(*[planner.generate(r) for r in requests])
    assert len(plans) == 3
    for plan in plans:
        assert len(plan.steps) >= 1
