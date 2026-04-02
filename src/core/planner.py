"""LM-Studio async planner."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import httpx

from src.core.models import Plan, PlanStep, UserRequest
from src.utils.config import load_config

_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "args": {"type": "object"},
                    "description": {"type": "string"},
                },
                "required": ["tool_name"],
            },
        },
        "reasoning": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["steps", "reasoning", "confidence"],
}

_SYSTEM_PROMPT = """\
You are a task-planning assistant. Given a user request, output a JSON plan with this schema:
{schema}
Return ONLY valid JSON – no markdown fences.
""".format(
    schema=json.dumps(_PLAN_SCHEMA, indent=2)
)


class LocalPlanner:
    """Async planner that calls LM-Studio to generate a Plan.

    Args:
        llm_semaphore: An asyncio.Semaphore(1) that serialises LLM requests.
                       If None, a new semaphore is created internally.
    """

    def __init__(self, llm_semaphore: asyncio.Semaphore | None = None) -> None:
        self._llm_semaphore = llm_semaphore or asyncio.Semaphore(1)
        self._cfg = load_config()

    async def generate(self, request: UserRequest) -> Plan:
        """Generate a Plan for the given UserRequest by calling LM-Studio.

        Args:
            request: The user's request to plan for.

        Returns:
            A Plan instance with one or more PlanSteps.

        Raises:
            RuntimeError: If the LLM response cannot be parsed into a Plan.
        """
        async with self._llm_semaphore:
            return await self._call_lmstudio(request)

    async def _call_lmstudio(self, request: UserRequest) -> Plan:
        """Perform the HTTP call to LM-Studio and parse the response.

        Args:
            request: The user's request.

        Returns:
            Validated Plan instance.

        Raises:
            RuntimeError: If the response is invalid or unparseable.
        """
        cfg = self._cfg.models
        url = f"{cfg.lmstudio_base_url}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": cfg.lmstudio_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": request.text},
            ],
            "max_tokens": cfg.max_tokens,
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"]
                return self._parse_plan(request.id, raw)
        except Exception as exc:
            raise RuntimeError(f"Planner failed: {exc}") from exc

    @staticmethod
    def _parse_plan(request_id: str, raw: str) -> Plan:
        """Parse raw LLM text output into a Plan.

        Args:
            request_id: ID of the originating UserRequest.
            raw: Raw text content from the LLM response.

        Returns:
            Parsed Plan instance.

        Raises:
            RuntimeError: If the JSON cannot be parsed or lacks required fields.
        """
        try:
            data = json.loads(raw)
            steps = [
                PlanStep(
                    id=str(uuid.uuid4()),
                    tool_name=s["tool_name"],
                    args=s.get("args", {}),
                    description=s.get("description", ""),
                )
                for s in data.get("steps", [])
            ]
            return Plan(
                request_id=request_id,
                steps=steps,
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.0)),
            )
        except Exception as exc:
            raise RuntimeError(f"Planner failed: {exc}") from exc


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
