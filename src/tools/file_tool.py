"""Safe file read/write tool with path-whitelisting."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.core.models import RiskLevel, ToolResult
from src.tools.base import BaseTool

_USER_DATA_DIR = Path(os.environ.get("USER_DATA_DIR", "user_data")).resolve()


class FileTool(BaseTool):
    """Read or write files restricted to the configured user_data directory.

    Attributes:
        name: Tool identifier.
        description: Human-readable description.
        risk: Risk level classification.
        schema: JSON-Schema for accepted arguments.
    """

    name: str = "file_tool"
    description: str = "Read or write files inside the user_data directory."
    risk: RiskLevel = RiskLevel.SAFE
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "write"]},
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["action", "path"],
    }

    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate file operation arguments and path whitelist.

        Args:
            action: 'read' or 'write'.
            path: Relative or absolute file path.
            content: File content (required for 'write').

        Returns:
            Tuple of (is_valid, error_message).
        """
        action = kwargs.get("action")
        path_str = kwargs.get("path", "")
        if action not in ("read", "write"):
            return False, f"Unknown action '{action}'; must be 'read' or 'write'."
        if not path_str:
            return False, "path must not be empty."
        resolved = (Path(path_str) if Path(path_str).is_absolute() else _USER_DATA_DIR / path_str).resolve()
        if not str(resolved).startswith(str(_USER_DATA_DIR)):
            return False, f"Path '{resolved}' is outside the allowed directory."
        if action == "write" and not kwargs.get("content"):
            return False, "content must be provided for write operations."
        return True, ""

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute a file read or write operation.

        Args:
            action: 'read' or 'write'.
            path: Path relative to user_data_dir (or absolute within it).
            content: Text to write (only for 'write').

        Returns:
            ToolResult with file content on read, or confirmation on write.
        """
        try:
            valid, msg = await self.validate(**kwargs)
            if not valid:
                return ToolResult(success=False, error=msg)
            action = kwargs["action"]
            path_str = kwargs["path"]
            resolved = (Path(path_str) if Path(path_str).is_absolute() else _USER_DATA_DIR / path_str).resolve()
            if action == "read":
                if not resolved.exists():
                    return ToolResult(success=False, error=f"File not found: {resolved}")
                content = resolved.read_text(encoding="utf-8")
                return ToolResult(success=True, output=content)
            else:
                resolved.parent.mkdir(parents=True, exist_ok=True)
                resolved.write_text(kwargs.get("content", ""), encoding="utf-8")
                return ToolResult(success=True, output=f"Written to {resolved}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
