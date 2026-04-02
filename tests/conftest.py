"""Pytest fixtures shared across the test suite."""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def event_loop():
    """Create a new asyncio event loop for each test.

    Returns:
        asyncio.AbstractEventLoop: A fresh event loop.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_lmstudio(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Fixture that patches httpx.AsyncClient to return a deterministic plan.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        AsyncMock configured to return a valid LM-Studio response.
    """
    plan_payload = json.dumps(
        {
            "steps": [
                {
                    "tool_name": "shell_tool",
                    "args": {"command": "echo", "args": ["hello"]},
                    "description": "Echo hello",
                }
            ],
            "reasoning": "Test plan",
            "confidence": 0.95,
        }
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": plan_payload}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: mock_client)
    return mock_client


@pytest.fixture
def tmp_user_data(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Set USER_DATA_DIR to a temporary directory for file-tool tests.

    Args:
        tmp_path: Pytest tmp_path fixture.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        pathlib.Path: Temporary directory path.
    """
    monkeypatch.setenv("USER_DATA_DIR", str(tmp_path))
    return tmp_path
