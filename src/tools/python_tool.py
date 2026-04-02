"""Sandboxed Python code execution tool."""
from __future__ import annotations

import asyncio
import sys
from typing import Any

from src.core.models import RiskLevel, ToolResult
from src.tools.base import BaseTool
from src.safety.sandbox import validate_python_imports

_DEFAULT_TIMEOUT = 30.0
_FORBIDDEN_BUILTINS = ["__import__", "open", "eval", "exec", "compile"]

_SANDBOX_WRAPPER = """\
import sys

_allowed_builtins = {{k: v for k, v in __builtins__.items() if k not in {forbidden!r}}}

_code = sys.stdin.read()
exec(compile(_code, "<sandbox>", "exec"), {{"__builtins__": _allowed_builtins}})
"""


class PythonTool(BaseTool):
    """Execute sandboxed Python code in a subprocess with import restrictions.

    Attributes:
        name: Tool identifier.
        description: Human-readable description.
        risk: Risk level classification.
        schema: JSON-Schema for accepted arguments.
    """

    name: str = "python_tool"
    description: str = "Execute Python code in a sandboxed subprocess."
    risk: RiskLevel = RiskLevel.DANGEROUS
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "number"},
        },
        "required": ["code"],
    }

    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate that the code does not import forbidden modules.

        Args:
            code: Python source code to validate.
            timeout: Optional timeout in seconds.

        Returns:
            Tuple of (is_valid, error_message).
        """
        code = kwargs.get("code", "")
        if not code.strip():
            return False, "code must not be empty."
        valid, msg = validate_python_imports(code)
        return valid, msg

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Spawn a subprocess to run the provided Python code.

        Args:
            code: Python source code to execute.
            timeout: Execution timeout in seconds (default 30).

        Returns:
            ToolResult with stdout as output or error message.
        """
        try:
            valid, msg = await self.validate(**kwargs)
            if not valid:
                return ToolResult(success=False, error=msg)
            code: str = kwargs["code"]
            timeout: float = float(kwargs.get("timeout", _DEFAULT_TIMEOUT))
            wrapper = _SANDBOX_WRAPPER.format(forbidden=_FORBIDDEN_BUILTINS)
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                wrapper,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=code.encode()), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(success=False, error=f"Code execution timed out after {timeout}s")
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
