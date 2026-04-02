"""Email composition and sending tool with mandatory confirmation."""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from src.core.models import RiskLevel, ToolResult
from src.tools.base import BaseTool


class EmailTool(BaseTool):
    """Compose and send emails via SMTP-SSL after a confirmation step.

    A confirmation gate is enforced before every send; the tool returns
    a failure result if confirmation is denied.

    Attributes:
        name: Tool identifier.
        description: Human-readable description.
        risk: Risk level classification.
        schema: JSON-Schema for accepted arguments.
    """

    name: str = "email_tool"
    description: str = "Compose and send an email after user confirmation."
    risk: RiskLevel = RiskLevel.MODERATE
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "smtp_host": {"type": "string"},
            "smtp_port": {"type": "integer", "default": 465},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "confirmed": {"type": "boolean", "default": False},
        },
        "required": ["to", "subject", "body", "smtp_host", "username", "password"],
    }

    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate email arguments.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Email body text.
            smtp_host: SMTP server hostname.
            username: SMTP authentication username.
            password: SMTP authentication password.
            confirmed: Must be True to actually send.

        Returns:
            Tuple of (is_valid, error_message).
        """
        for field in ("to", "subject", "body", "smtp_host", "username", "password"):
            if not kwargs.get(field):
                return False, f"'{field}' is required."
        return True, ""

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Send the email after validating and checking confirmation.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body: Email body.
            smtp_host: SMTP server hostname.
            smtp_port: SMTP port (default 465).
            username: SMTP username.
            password: SMTP password.
            confirmed: Must be True to proceed with sending.

        Returns:
            ToolResult indicating success or failure.
        """
        try:
            valid, msg = await self.validate(**kwargs)
            if not valid:
                return ToolResult(success=False, error=msg)
            if not kwargs.get("confirmed", False):
                return ToolResult(
                    success=False,
                    error="Email not sent: confirmation required. Set 'confirmed': true to proceed.",
                )
            message = EmailMessage()
            message["To"] = kwargs["to"]
            message["Subject"] = kwargs["subject"]
            message["From"] = kwargs["username"]
            message.set_content(kwargs["body"])
            context = ssl.create_default_context()
            port = int(kwargs.get("smtp_port", 465))
            with smtplib.SMTP_SSL(kwargs["smtp_host"], port, context=context) as server:
                server.login(kwargs["username"], kwargs["password"])
                server.send_message(message)
            return ToolResult(success=True, output=f"Email sent to {kwargs['to']}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
