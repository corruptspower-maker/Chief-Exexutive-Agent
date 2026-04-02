"""JSON structured logging configuration using loguru."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger

_LOG_DIR = Path("logs")
_LOG_FILE = _LOG_DIR / "agent.log"
_configured = False


def configure_logging(debug: bool = False) -> None:
    """Configure loguru to write JSON lines to logs/agent.log.

    Args:
        debug: If True, also logs DEBUG-level messages.

    Returns:
        None
    """
    global _configured
    if _configured:
        return
    _LOG_DIR.mkdir(exist_ok=True)
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    # JSON sink to file
    logger.add(
        str(_LOG_FILE),
        level=level,
        serialize=True,
        rotation="10 MB",
        retention="7 days",
        enqueue=True,
    )
    # Human-readable sink to stderr
    logger.add(sys.stderr, level=level, enqueue=True)
    _configured = True


def json_log(event: str, **payload: Any) -> None:
    """Emit a structured JSON log entry.

    Args:
        event: Short event name describing what happened.
        **payload: Additional key-value pairs to include in the log record.

    Returns:
        None
    """
    logger.info(event, **payload)


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
