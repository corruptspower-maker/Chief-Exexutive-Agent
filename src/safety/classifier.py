"""Static risk classifier for tools and actions."""
from __future__ import annotations

from src.core.models import RiskLevel

_TOOL_RISK_MAP: dict[str, RiskLevel] = {
    "file_tool": RiskLevel.SAFE,
    "web_search_tool": RiskLevel.SAFE,
    "python_tool": RiskLevel.DANGEROUS,
    "shell_tool": RiskLevel.DANGEROUS,
    "browser_tool": RiskLevel.DANGEROUS,
    "email_tool": RiskLevel.MODERATE,
}

_DEFAULT_RISK = RiskLevel.MODERATE


def classify(tool_name: str, args: dict[str, object]) -> RiskLevel:
    """Classify the risk level of a tool invocation.

    Args:
        tool_name: Registered name of the tool (e.g. 'shell_tool').
        args: Arguments that will be passed to the tool.

    Returns:
        RiskLevel for the given tool, or MODERATE if unknown.
    """
    return _TOOL_RISK_MAP.get(tool_name, _DEFAULT_RISK)


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
