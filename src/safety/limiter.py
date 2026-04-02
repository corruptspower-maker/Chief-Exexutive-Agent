"""Token-bucket rate limiter per action."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import yaml

_SAFETY_YAML = Path(__file__).parents[2] / "config" / "safety.yaml"


def _load_rate_limits() -> dict[str, int]:
    """Load per-action rate limits (tokens per minute) from safety.yaml.

    Returns:
        Mapping of action name to tokens-per-minute allowance.
    """
    try:
        with open(_SAFETY_YAML) as f:
            data = yaml.safe_load(f)
        return data.get("rate_limits", {})
    except Exception:
        return {}


class _TokenBucket:
    """Simple token-bucket implementation.

    Args:
        capacity: Maximum number of tokens.
        refill_rate: Tokens added per second.
    """

    def __init__(self, capacity: float, refill_rate: float) -> None:
        self._capacity = capacity
        self._tokens = capacity
        self._refill_rate = refill_rate
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def consume(self, amount: float = 1.0) -> bool:
        """Consume tokens; return True if allowed, False if rate-limited.

        Args:
            amount: Number of tokens to consume.

        Returns:
            True if enough tokens were available, False otherwise.
        """
        self._refill()
        if self._tokens >= amount:
            self._tokens -= amount
            return True
        return False


_buckets: dict[str, _TokenBucket] = {}
_lock = asyncio.Lock()


async def allow(action: str) -> bool:
    """Check whether an action is allowed under the current rate limit.

    Args:
        action: Action name matching an entry in safety.yaml rate_limits.

    Returns:
        True if the action is allowed, False if rate-limited.
    """
    async with _lock:
        if action not in _buckets:
            limits = _load_rate_limits()
            # tokens_per_minute -> tokens_per_second
            tpm = limits.get(action, 60)
            _buckets[action] = _TokenBucket(capacity=float(tpm), refill_rate=float(tpm) / 60.0)
        return _buckets[action].consume()


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
