"""Rich-based interactive CLI for Chief Executive Agent."""
from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.executive import ExecutiveAgent
from src.core.models import StepStatus
from src.core.planner import LocalPlanner
from src.core.tool_router import ToolRouter
from src.escalation.manager import EscalationManager
from src.safety.audit_log import AuditLog
from src.safety.confirmation import ConfirmationProtocol
from src.utils.config import load_config
from src.utils.logging import configure_logging

console = Console()


def _build_agent() -> ExecutiveAgent:
    """Construct and return a fully wired ExecutiveAgent.

    Returns:
        Configured ExecutiveAgent instance.
    """
    cfg = load_config()
    configure_logging(cfg.debug)
    planner = LocalPlanner()
    router = ToolRouter()
    escalation = EscalationManager()
    audit = AuditLog()
    safety = ConfirmationProtocol()
    return ExecutiveAgent(planner, router, escalation, audit, safety)


async def _run_interactive(agent: ExecutiveAgent) -> None:
    """Run the interactive REPL loop.

    Args:
        agent: The ExecutiveAgent to process requests.

    Returns:
        None
    """
    console.print("[bold cyan]Chief Executive Agent[/bold cyan] – type 'exit' to quit.\n")
    while True:
        try:
            text = click.prompt(">>>", prompt_suffix=" ")
        except (EOFError, KeyboardInterrupt):
            break
        if text.strip().lower() in {"exit", "quit"}:
            break
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Processing…", total=None)
            task = await agent.process(text)
        console.print(f"\n[bold]Task {task.id} → {task.status.value}[/bold]")
        if task.plan:
            for step in task.plan.steps:
                icon = "✅" if step.status == StepStatus.COMPLETED else "❌"
                console.print(f"  [{icon}] {step.description or step.tool_name}")
        if task.error:
            console.print(f"  [red]Error: {task.error}[/red]")
        console.print()


@click.command()
def main() -> None:
    """Start the Chief Executive Agent CLI."""
    agent = _build_agent()
    asyncio.run(_run_interactive(agent))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
    main()
