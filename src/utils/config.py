"""Configuration loader for Chief Executive Agent."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SafetyConfig(BaseModel):
    """Safety-related configuration fields.

    Args:
        command_whitelist: Allowed shell command prefixes.
        forbidden_imports: Python modules that must not be imported in sandboxed code.
        rate_limits: Per-action token-bucket limits (action -> tokens per minute).

    Returns:
        SafetyConfig instance.
    """

    command_whitelist: list[str] = Field(default_factory=list)
    forbidden_imports: list[str] = Field(default_factory=list)
    rate_limits: dict[str, int] = Field(default_factory=dict)


class ModelsConfig(BaseModel):
    """LLM / browser model configuration.

    Args:
        lmstudio_base_url: Base URL for LM-Studio API.
        lmstudio_model: Model identifier.
        max_tokens: Maximum token budget for a single LLM call.
        timeout_seconds: HTTP timeout for LLM requests.
        chrome_profile_dir: Path to the Chrome user-data directory for Tier-3.

    Returns:
        ModelsConfig instance.
    """

    lmstudio_base_url: str = "http://localhost:1234"
    lmstudio_model: str = "local-model"
    max_tokens: int = 8192
    timeout_seconds: float = 60.0
    chrome_profile_dir: str = ""


class EscalationConfig(BaseModel):
    """Escalation tuning parameters.

    Args:
        max_retries: Number of retries before escalating a step.
        circuit_breaker_threshold: Failures before the circuit opens.
        circuit_breaker_reset_seconds: Seconds before circuit tries to close.

    Returns:
        EscalationConfig instance.
    """

    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: float = 60.0


class AgentConfig(BaseModel):
    """Top-level agent configuration.

    Args:
        debug: Enable verbose debug logging.
        max_concurrent_tasks: Maximum number of tasks running in parallel.
        user_data_dir: Base directory for file-tool access (whitelist root).
        safety: Safety configuration sub-section.
        models: Model configuration sub-section.
        escalation: Escalation configuration sub-section.

    Returns:
        AgentConfig instance.
    """

    debug: bool = False
    max_concurrent_tasks: int = 3
    user_data_dir: str = "user_data"
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)


def load_config() -> AgentConfig:
    """Load agent configuration from config/agent.yaml.

    Returns:
        AgentConfig: Validated configuration object.

    Raises:
        FileNotFoundError: If agent.yaml does not exist.
        ValidationError: If the YAML content fails Pydantic validation.
    """
    config_path = Path(__file__).parents[2] / "config" / "agent.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return AgentConfig(**(data or {}))


def load_yaml(path: str, schema: type[BaseModel]) -> BaseModel:
    """Load any YAML file and validate it against a Pydantic schema.

    Args:
        path: Filesystem path to the YAML file.
        schema: Pydantic BaseModel subclass to validate against.

    Returns:
        Validated Pydantic model instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValidationError: If the content fails validation.
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return schema(**(data or {}))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
