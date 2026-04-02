"""User confirmation protocol for high-risk actions."""
from __future__ import annotations

import asyncio
import sys

import click


class ConfirmationProtocol:
    """Prompt the user for confirmation before a dangerous action.

    Provides a ``ask`` method that blocks asynchronously waiting for a
    ``y`` or ``n`` response from the operator.
    """

    async def ask(self, user_prompt: str) -> bool:
        """Display a confirmation prompt and wait for a yes/no answer.

        Args:
            user_prompt: The question or description of the action to confirm.

        Returns:
            True if the user confirmed, False otherwise.
        """
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, self._prompt_sync, user_prompt)
        return answer

    @staticmethod
    def _prompt_sync(user_prompt: str) -> bool:
        """Blocking synchronous prompt (runs in a thread-pool executor).

        Args:
            user_prompt: Question to display.

        Returns:
            True if the user typed 'y', False otherwise.
        """
        try:
            answer = click.prompt(
                f"\n⚠️  CONFIRMATION REQUIRED\n{user_prompt}\nProceed? [y/n]",
                default="n",
                show_default=True,
            )
            return str(answer).strip().lower() == "y"
        except (EOFError, KeyboardInterrupt):
            return False


async def ask(user_prompt: str) -> bool:
    """Module-level helper: ask for user confirmation.

    Args:
        user_prompt: Description of the action requiring confirmation.

    Returns:
        True if the user confirmed, False otherwise.
    """
    protocol = ConfirmationProtocol()
    return await protocol.ask(user_prompt)


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
