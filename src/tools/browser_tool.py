"""Browser automation tool (Tier-3 escalation) via Playwright."""
from __future__ import annotations

import os
from typing import Any

from src.core.models import RiskLevel, ToolResult
from src.tools.base import BaseTool

_CHROME_PROFILE = os.environ.get("CHROME_PROFILE_DIR", "")


class BrowserTool(BaseTool):
    """Automate the browser using Playwright for Tier-3 escalation tasks.

    Opens the configured Chrome profile, navigates to a URL, submits a prompt,
    and extracts a response. This is a minimal, Tier-3-only implementation.

    Attributes:
        name: Tool identifier.
        description: Human-readable description.
        risk: Risk level classification.
        schema: JSON-Schema for accepted arguments.
    """

    name: str = "browser_tool"
    description: str = "Automate a browser to submit a prompt and extract a response."
    risk: RiskLevel = RiskLevel.DANGEROUS
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "prompt": {"type": "string"},
            "input_selector": {"type": "string"},
            "response_selector": {"type": "string"},
            "timeout_ms": {"type": "integer", "default": 30000},
        },
        "required": ["url", "prompt"],
    }

    async def validate(self, **kwargs: Any) -> tuple[bool, str]:
        """Validate browser tool arguments.

        Args:
            url: Target URL to navigate to.
            prompt: Text prompt to enter in the browser.
            input_selector: CSS selector for the input element.
            response_selector: CSS selector for the response element.
            timeout_ms: Playwright action timeout in milliseconds.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not kwargs.get("url"):
            return False, "url must not be empty."
        if not kwargs.get("prompt"):
            return False, "prompt must not be empty."
        return True, ""

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Launch Playwright, navigate, submit the prompt, and return the response.

        Args:
            url: URL to navigate to.
            prompt: Text to type into the input element.
            input_selector: CSS selector for the text input (default 'textarea').
            response_selector: CSS selector to wait for the response (default '.response').
            timeout_ms: Timeout in milliseconds (default 30000).

        Returns:
            ToolResult with the extracted response text.
        """
        try:
            valid, msg = await self.validate(**kwargs)
            if not valid:
                return ToolResult(success=False, error=msg)
            from playwright.async_api import async_playwright  # local import

            url: str = kwargs["url"]
            prompt_text: str = kwargs["prompt"]
            input_sel: str = kwargs.get("input_selector", "textarea")
            response_sel: str = kwargs.get("response_selector", ".response")
            timeout_ms: int = int(kwargs.get("timeout_ms", 30000))

            async with async_playwright() as pw:
                launch_args: dict[str, Any] = {"headless": False}
                if _CHROME_PROFILE:
                    launch_args["user_data_dir"] = _CHROME_PROFILE
                    browser = await pw.chromium.launch_persistent_context(**launch_args)
                    page = await browser.new_page()
                else:
                    browser_instance = await pw.chromium.launch(headless=True)
                    page = await browser_instance.new_page()
                await page.goto(url, timeout=timeout_ms)
                await page.fill(input_sel, prompt_text)
                await page.keyboard.press("Enter")
                await page.wait_for_selector(response_sel, timeout=timeout_ms)
                response_text = await page.inner_text(response_sel)
                return ToolResult(success=True, output=response_text)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
