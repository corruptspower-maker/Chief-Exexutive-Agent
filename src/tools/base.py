"""Abstract base class for all agent tools."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.core.models import RiskLevel, ToolResult


class BaseTool(ABC):
    """Abstract base for every tool the agent can invoke.

    Subclasses must define ``name``, ``description``, ``risk``, ``schema``,
    and implement ``execute`` and ``validate``.
    """

    name: str
    description: str
    risk: RiskLevel
    schema: dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the provided arguments.

        Args:
            **kwargs: Tool-specific arguments matching ``schema``.

        Returns:
            ToolResult indicating success or failure.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        ...

    @abstractmethod
    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate arguments before execution.

        Args:
            **kwargs: Tool-specific arguments to validate.

        Returns:
            Tuple of (is_valid, error_message). error_message is empty when valid.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        ...

    def prompt_description(self) -> str:
        """Return a one-line description suitable for inclusion in a prompt.

        Returns:
            String describing the tool name, risk level, and description.
        """
        return f"[{self.risk.value.upper()}] {self.name}: {self.description}"


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
