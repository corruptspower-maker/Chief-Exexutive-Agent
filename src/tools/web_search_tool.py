"""Web search tool (mocked for initial implementation)."""
from __future__ import annotations

import json
from typing import Any

import httpx

from src.core.models import RiskLevel, ToolResult
from src.tools.base import BaseTool

_MOCK_RESULTS = [
    {"title": "Example Result 1", "url": "https://example.com/1", "snippet": "Mock snippet 1"},
    {"title": "Example Result 2", "url": "https://example.com/2", "snippet": "Mock snippet 2"},
]


class WebSearchTool(BaseTool):
    """Perform an async web search and return JSON results.

    Uses a mock payload by default; swap the URL for a real search API
    when integrating with a live service.

    Attributes:
        name: Tool identifier.
        description: Human-readable description.
        risk: Risk level classification.
        schema: JSON-Schema for accepted arguments.
    """

    name: str = "web_search_tool"
    description: str = "Search the web and return a JSON list of results."
    risk: RiskLevel = RiskLevel.SAFE
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "num_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }

    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate web-search arguments.

        Args:
            query: The search query string.
            num_results: Number of results to return.

        Returns:
            Tuple of (is_valid, error_message).
        """
        query = kwargs.get("query", "")
        if not query.strip():
            return False, "query must not be empty."
        return True, ""

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute a web search and return results as a JSON string.

        Args:
            query: The search query string.
            num_results: Maximum number of results (default 5).

        Returns:
            ToolResult with JSON-encoded search results.
        """
        try:
            valid, msg = await self.validate(**kwargs)
            if not valid:
                return ToolResult(success=False, error=msg)
            # Mock implementation – real endpoint would be called here
            results = _MOCK_RESULTS[: int(kwargs.get("num_results", 5))]
            return ToolResult(success=True, output=json.dumps(results))
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
