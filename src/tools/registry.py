"""Auto-discovery registry for BaseTool subclasses."""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tools.base import BaseTool

TOOL_REGISTRY: dict[str, type["BaseTool"]] = {}


def _discover_tools() -> None:
    """Discover and register all BaseTool subclasses in the src/tools package.

    Iterates over modules in the ``src.tools`` package, imports each one, and
    registers any concrete ``BaseTool`` subclass found therein.

    Returns:
        None
    """
    from src.tools.base import BaseTool  # local import to avoid circular deps

    tools_path = Path(__file__).parent
    package_name = "src.tools"

    for module_info in pkgutil.iter_modules([str(tools_path)]):
        if module_info.name in ("base", "registry"):
            continue
        try:
            module = importlib.import_module(f"{package_name}.{module_info.name}")
        except Exception:  # pragma: no cover
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            try:
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseTool)
                    and attr is not BaseTool
                    and not getattr(attr, "__abstractmethods__", None)
                ):
                    instance = attr()
                    TOOL_REGISTRY[instance.name] = attr
            except Exception:  # pragma: no cover
                continue


_discover_tools()

if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
