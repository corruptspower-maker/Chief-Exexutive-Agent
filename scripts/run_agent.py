"""Entry point script for Chief Executive Agent."""
from __future__ import annotations

import asyncio

from src.core.executive import ExecutiveAgent
from src.core.planner import LocalPlanner
from src.core.tool_router import ToolRouter
from src.escalation.manager import EscalationManager
from src.safety.audit_log import AuditLog
from src.safety.confirmation import ConfirmationProtocol
from src.utils.config import load_config
from src.utils.logging import configure_logging


async def main() -> None:
    """Build the agent and run the interactive REPL."""
    cfg = load_config()
    configure_logging(cfg.debug)
    planner = LocalPlanner()
    router = ToolRouter()
    escalation = EscalationManager()
    audit = AuditLog()
    safety = ConfirmationProtocol()
    agent = ExecutiveAgent(planner, router, escalation, audit, safety)

    while True:
        try:
            txt = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            break
        if txt.strip().lower() in {"exit", "quit"}:
            break
        task = await agent.process(txt)
        print(f"Task {task.id} finished with status {task.status.value}")


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
    asyncio.run(main())
