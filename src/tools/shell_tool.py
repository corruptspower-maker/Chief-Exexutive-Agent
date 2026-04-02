"""Shell command execution tool with whitelist enforcement."""
from __future__ import annotations

import asyncio
from typing import Any

import yaml
from pathlib import Path

from src.core.models import RiskLevel, ToolResult
from src.tools.base import BaseTool

_SAFETY_YAML = Path(__file__).parents[2] / "config" / "safety.yaml"


def _load_whitelist() -> list[str]:
    """Load the shell command whitelist from safety.yaml.

    Returns:
        List of allowed command prefixes.
    """
    try:
        with open(_SAFETY_YAML) as f:
            data = yaml.safe_load(f)
        return data.get("command_whitelist", [])
    except Exception:
        return []


class ShellTool(BaseTool):
    """Execute whitelisted shell commands via asyncio subprocess.

    Attributes:
        name: Tool identifier.
        description: Human-readable description.
        risk: Risk level classification.
        schema: JSON-Schema for accepted arguments.
    """

    name: str = "shell_tool"
    description: str = "Run whitelisted shell commands and return stdout/stderr."
    risk: RiskLevel = RiskLevel.DANGEROUS
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "args": {"type": "array", "items": {"type": "string"}},
            "timeout": {"type": "number"},
        },
        "required": ["command"],
    }

    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Check that the command is in the whitelist.

        Args:
            command: The executable name.
            args: Optional list of string arguments.
            timeout: Optional timeout in seconds.

        Returns:
            Tuple of (is_valid, error_message).
        """
        command = kwargs.get("command", "")
        whitelist = _load_whitelist()
        if not any(command == allowed or command.startswith(allowed + " ") for allowed in whitelist):
            return False, f"Command '{command}' is not in the allowed whitelist."
        return True, ""

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the shell command and capture output.

        Args:
            command: Executable name (e.g. 'echo').
            args: List of string arguments.
            timeout: Execution timeout in seconds (default 30).

        Returns:
            ToolResult with stdout as output or stderr as error.
        """
        try:
            valid, msg = await self.validate(**kwargs)
            if not valid:
                return ToolResult(success=False, error=msg)
            command = kwargs["command"]
            args: list[str] = kwargs.get("args", [])
            timeout: float = float(kwargs.get("timeout", 30))
            proc = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(success=False, error=f"Command timed out after {timeout}s")
            if proc.returncode != 0:
                return ToolResult(
                    success=False,
                    output=stdout.decode(errors="replace"),
                    error=stderr.decode(errors="replace"),
                )
            return ToolResult(success=True, output=stdout.decode(errors="replace"))
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
