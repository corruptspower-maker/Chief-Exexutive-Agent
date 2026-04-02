"""Input validation and sandboxing helpers."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

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


def _load_forbidden_imports() -> list[str]:
    """Load the list of forbidden Python module names from safety.yaml.

    Returns:
        List of module name strings that must not be imported.
    """
    try:
        with open(_SAFETY_YAML) as f:
            data = yaml.safe_load(f)
        return data.get("forbidden_imports", [])
    except Exception:
        return []


def validate_shell(command: str) -> tuple[bool, str]:
    """Validate a shell command string against the whitelist.

    Args:
        command: The full command string to validate.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty when valid.
    """
    whitelist = _load_whitelist()
    cmd_name = command.strip().split()[0] if command.strip() else ""
    for allowed in whitelist:
        # Match exact command name or the allowed prefix
        pattern = r"^" + re.escape(allowed) + r"(\s|$)"
        if re.match(pattern, command.strip()):
            return True, ""
    return False, f"Command '{cmd_name}' is not in the allowed whitelist."


def validate_python_imports(code: str) -> tuple[bool, str]:
    """Parse Python code with ast and detect forbidden import statements.

    Args:
        code: Python source code string.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty when valid.

    Raises:
        None: SyntaxErrors are caught and returned as validation failures.
    """
    forbidden = _load_forbidden_imports()
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"Syntax error in code: {exc}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden:
                    return False, f"Import of forbidden module '{root}' is not allowed."
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in forbidden:
                    return False, f"Import of forbidden module '{root}' is not allowed."
    return True, ""


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
