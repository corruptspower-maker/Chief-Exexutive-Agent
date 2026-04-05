# Executive Agent System — Complete Build Specification

## INSTRUCTIONS FOR COPILOT AGENT
Build a production-grade GitHub repository from scratch. Use the best model available (Opus-tier). Follow this spec exactly. Build each phase completely with passing tests before starting the next. Every file needs docstrings, type hints, and tests. No shortcuts, no stubs.

When you encounter an ambiguity not covered by this spec, make the simplest possible choice, document your decision in `DECISIONS.md` at the repo root, and continue. Do not ask for clarification — decide and document.

---

## 1. WHAT THIS IS

A **Personal Executive Agent** — a local AI operator that runs continuously on Windows, breaks user requests into steps, executes tasks with tools, escalates to more capable AI systems when needed, and learns from every interaction.

**This is not a chatbot. This is an autonomous task executor with planning, tools, tiered escalation, memory, safety, and self-improvement.**

### Local Brain
- **Model:** `huihui-qwen3.5-9b-abliterated-ties-i1` (Q4_K_S) via LM Studio on `localhost:1234`
- **Hardware:** NVIDIA RTX 3060 12GB, Windows OS
- **Context:** ~32K tokens (8K system, 8K memory, 16K conversation)

### Escalation Brain (NO API BILLING)
User has paid subscriptions. Agent orchestrates existing tools, NOT billed API calls.

| Tier | Interface | Cost Model | Timeout | Best For |
|------|-----------|------------|---------|----------|
| 1 | GitHub Copilot API (OpenAI-compat) | Subscription, zero marginal cost | 30s | Code generation, quick fixes |
| 2 | Claude Code CLI subprocess | Subscription quota, zero marginal cost | 300s | Architecture, multi-file refactor |
| 3 | Cline in VS Code (via Claude Code) | Subscription, zero marginal cost | 600s | Long agentic coding sessions |

---

## 2. ARCHITECTURAL CONSTRAINTS

### Language & Runtime
- Python 3.11+ on Windows, async throughout (`asyncio`)
- Type hints on every function. No `Any` unless unavoidable.
- Pydantic v2 for ALL data models.

### Dependencies
**Installation Order (Critical):**
1. `httpx>=0.25.0` (HTTP client)
2. `pydantic>=2.5.0,<3.0.0` (data models - v2 only)
3. `chromadb>=0.4.15` (semantic memory - optional, with fallback)
4. `click>=8.1.0` (CLI framework)
5. `loguru>=0.7.0` (logging)
6. `tenacity>=8.2.0` (retry logic)
7. `rich>=13.7.0` (terminal UI)
8. `fastapi>=0.104.0` (web framework)
9. `uvicorn[standard]>=0.24.0` (ASGI server)
10. `jinja2>=3.1.0` (templating)
11. `python-dotenv>=1.0.0` (environment variables)
12. `pyyaml>=6.0.0` (YAML config)
13. `mss>=9.0.0` (screenshots)
14. `pillow>=10.1.0` (image processing)
15. `aiosqlite>=0.19.0` (async SQLite)
16. `websockets>=12.0` (WebSocket support)

**Version Constraints:** Pin major versions in pyproject.toml, allow patch updates. Use `>=` for minimum versions, `<` for upper bounds where breaking changes expected.

### What NOT to use
- NO LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex
- NO per-token API billing

### Configuration
- All config in `config/*.yaml`
- Environment variables for secrets only (`.env`)

### Testing
**Framework:** pytest + pytest-asyncio + pytest-cov + pytest-mock

**Test Categories:**
- **Unit Tests:** All Pydantic models, safety classifier, rate limiter, circuit breaker, memory manager, tool validation
- **Integration Tests:** Full agent loop end-to-end, MCP server interactions, escalation chains, memory persistence
- **Chaos Tests:** Network failures, LM Studio timeouts, ChromaDB failures, circuit breaker triggers
- **Performance Tests:** Memory usage, response times, concurrent task handling

**Coverage Requirements:**
- Core modules (core/, safety/): ≥90% coverage
- Tool modules: ≥80% coverage
- Memory modules: ≥85% coverage
- Integration tests: Cover all success criteria in Section 15
- Chaos tests: Cover failure modes and recovery

**Test Data:** Use factories for test data. Mock external services (LM Studio, ChromaDB). Use temporary directories for file operations.

**CI Enforcement:** Tests run on every commit. Coverage reports uploaded. No merge without passing tests. Run: `pytest --cov=src --cov-report=term-missing` to verify locally.

### Code Quality
**Linting:** ruff with strict configuration. Enforce in CI with `--fix` on format violations.

**Type Hints:** Required on all public interfaces, data models, and complex private functions. Use `typing_extensions` for Python 3.11+ features if needed.

**Error Handling:**
- No bare `except:` in core/ and safety/ modules — catch specific exceptions only
- MCP tool handlers and executor may use broad exception catching by design
- Log all exceptions with context, never swallow silently
- Return structured error responses, not raw exceptions

**Documentation:** Google-style docstrings on all public functions/classes. Include examples for complex APIs.

**Security:** Input validation on all external inputs. No eval/exec. Sandbox all dynamic code execution.

---

## 3. REPOSITORY STRUCTURE

```
executive-agent/
├── pyproject.toml, .env.example, .gitignore, README.md, Makefile, DECISIONS.md
├── config/
│   ├── agent.yaml, models.yaml, tools.yaml, memory.yaml
│   ├── safety.yaml, escalation.yaml, ui.yaml, mcp.yaml
├── src/
│   ├── core/          # executive.py, planner.py, reasoner.py, tool_router.py, executor.py, models.py
│   ├── mcp_servers/   # Agent's own MCP server (exposes agent to Claude Code/Cline)
│   │                   # server.py, handlers.py, auth.py
│   ├── mcp_tools/     # Custom MCP tool servers the agent installs and uses
│   │                   # memory_server.py, state_server.py, screenshot_server.py, lmstudio_server.py
│   ├── escalation/    # detector.py, manager.py, circuit_breaker.py, request_builder.py, solution_applier.py, tier1_vscode.py, tier2_claude_code.py, tier3_browser.py
│   ├── memory/        # manager.py, conversation.py, episodic.py, semantic.py, procedural.py, user_profile.py
│   ├── tools/         # base.py, registry.py, file_tool.py, web_search_tool.py, email_tool.py, python_tool.py, shell_tool.py, rag_tool.py
│   ├── safety/        # confirmation.py, sandbox.py, action_classifier.py, rate_limiter.py, audit_log.py, safety_mode.py
│   ├── self_improvement/  # failure_analyzer.py, prompt_optimizer.py, tool_generator.py, workflow_learner.py
│   ├── interface/     # cli.py, web_ui.py (4-quadrant dashboard)
│   ├── observability/ # tracing.py, metrics.py, health.py
│   └── utils/        # logging.py, config.py, tokens.py, screenshot.py, lm_studio_client.py
├── tests/            # conftest.py, test_*.py, test_chaos/, test_integration/
├── data/             # checkpoint.json, heartbeat.json, screenshots/, databases/ — ALL gitignored
├── scripts/          # setup.ps1, run_agent.py, run_ui.bat, health_check.py
└── docs/             # ARCHITECTURE.md, TOOLS.md, ESCALATION.md, MEMORY.md, SAFETY.md, UI.md, MCP.md

**.gitignore must include:** `.env`, `data/`, `__pycache__/`, `*.pyc`, `.venv/`, `*.egg-info/`, `htmlcov/`, `.coverage`

**.env.example must contain:**
```
GITHUB_COPILOT_OAUTH_TOKEN=
GITHUB_COPILOT_REFRESH_TOKEN=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_APP_PASSWORD=
MCP_AUTH_SECRET=
```

Note: `src/mcp_servers/` = the agent's own MCP server (exposes agent to Claude Code). `src/mcp_tools/` = custom MCP tool servers the agent installs and uses. Never mix these two directories.

---

## 4. CORE DATA MODELS (src/core/models.py)

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import uuid4

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TaskStatus(str, Enum):
    PENDING = "pending"; PLANNING = "planning"; EXECUTING = "executing"
    ESCALATED = "escalated"; COMPLETED = "completed"; FAILED = "failed"; CANCELLED = "cancelled"

class RiskLevel(str, Enum):
    SAFE = "safe"; MODERATE = "moderate"; DANGEROUS = "dangerous"; FORBIDDEN = "forbidden"

class StepStatus(str, Enum):
    PENDING = "pending"; RUNNING = "running"; SUCCEEDED = "succeeded"
    FAILED = "failed"; SKIPPED = "skipped"; ESCALATED = "escalated"

class EscalationTier(str, Enum):
    TIER1_COPILOT = "tier1_copilot"
    TIER2_CLAUDE_CODE = "tier2_claude_code"
    TIER3_CLINE = "tier3_cline"

class EscalationReason(str, Enum):
    REPEATED_FAILURE = "repeated_failure"
    COMPLEXITY_EXCEEDED = "complexity_exceeded"
    CONFIDENCE_LOW = "confidence_low"
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    ARCHITECTURE_NEEDED = "architecture_needed"
    REASONING_DEPTH = "reasoning_depth"
    CONTEXT_OVERFLOW = "context_overflow"
    TIMEOUT = "timeout"
    USER_REQUEST = "user_request"
    MISSING_MCP_TOOL = "missing_mcp_tool"

class SafetyMode(str, Enum):
    FULL = "full"; LIGHT_BYPASS = "light_bypass"; MEDIUM_BYPASS = "medium_bypass"; SEVERE_LOCKED = "severe_locked"

class UserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); text: str
    source: str = "cli"; timestamp: datetime = Field(default_factory=utc_now)
    context: dict[str, Any] = Field(default_factory=dict)
    @field_validator("text")
    @classmethod
    def non_empty_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        return v
    @field_validator("timestamp")
    @classmethod
    def tz_aware_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware UTC")
        return v

class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); description: str
    tool_name: Optional[str] = None; tool_args: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING; result: Optional[str] = None
    error: Optional[str] = None; retry_count: int = 0; max_retries: int = 3
    @field_validator("description")
    @classmethod
    def non_empty_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description must not be empty")
        return v
    @field_validator("retry_count", "max_retries")
    @classmethod
    def non_negative_retry_values(cls, v: int) -> int:
        if v < 0:
            raise ValueError("retry values must be >= 0")
        return v

class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); task_id: str; steps: list[PlanStep]
    reasoning: str; created_at: datetime = Field(default_factory=utc_now)
    confidence: float = Field(ge=0.0, le=1.0)
    @field_validator("task_id", "reasoning")
    @classmethod
    def required_text_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("required text field cannot be empty")
        return v

class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_name: str; success: bool; output: Optional[str] = None; error: Optional[str] = None
    execution_time_ms: int = Field(default=0, ge=0); side_effects: list[str] = Field(default_factory=list)
    @field_validator("tool_name")
    @classmethod
    def non_empty_tool_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("tool_name must not be empty")
        return v

class EscalationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); reason: EscalationReason; tier: EscalationTier
    task_description: str; steps_attempted: list[PlanStep]; errors_encountered: list[str]
    current_code: Optional[str] = None; context: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    @field_validator("task_description")
    @classmethod
    def non_empty_task_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("task_description must not be empty")
        return v

class EscalationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str; tier_used: EscalationTier; tool_used: str; solution: str
    suggested_steps: list[str] = Field(default_factory=list); code_changes: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    @field_validator("request_id", "tool_used", "solution")
    @classmethod
    def non_empty_response_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("response text field cannot be empty")
        return v

class MemoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); category: str; content: str
    metadata: dict[str, Any] = Field(default_factory=dict); timestamp: datetime = Field(default_factory=utc_now)
    importance: float = Field(default=0.5, ge=0.0, le=1.0); access_count: int = 0
    @field_validator("category", "content")
    @classmethod
    def non_empty_memory_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("memory text field cannot be empty")
        return v
    @field_validator("access_count")
    @classmethod
    def non_negative_access_count(cls, v: int) -> int:
        if v < 0:
            raise ValueError("access_count must be >= 0")
        return v

class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); request: UserRequest
    status: TaskStatus = TaskStatus.PENDING; plan: Optional[Plan] = None
    results: list[ToolResult] = Field(default_factory=list)
    escalations: list[EscalationRequest] = Field(default_factory=list)
    started_at: Optional[datetime] = None; completed_at: Optional[datetime] = None
    error: Optional[str] = None
    @field_validator("started_at", "completed_at")
    @classmethod
    def optional_times_tz_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            raise ValueError("task timestamps must be timezone-aware UTC")
        return v

class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); timestamp: datetime = Field(default_factory=utc_now)
    action: str; tool_name: Optional[str] = None; risk_level: RiskLevel
    user_confirmed: Optional[bool] = None; input_summary: str; output_summary: Optional[str] = None
    success: bool; error: Optional[str] = None
    @field_validator("action", "input_summary")
    @classmethod
    def non_empty_audit_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("audit text field cannot be empty")
        return v

class ScreenshotEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid4())); image_path: str
    description: str; timestamp: datetime = Field(default_factory=utc_now)
    action_taken: Optional[str] = None
    @field_validator("image_path", "description")
    @classmethod
    def non_empty_screenshot_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("screenshot text field cannot be empty")
        return v
```

---

## 5. EXECUTIVE AGENT LOOP (src/core/executive.py)

**Startup:**
1. Check port availability — use `socket.connect_ex()` to test ports 8765 and 8000 before binding. If either port is in use, print error message naming the conflicting port and exit immediately. Do not start the agent with a port conflict.
2. Load checkpoint
3. Init subsystems
4. Verify LM Studio
5. Start heartbeat

**Main Loop:** Receive Request → Retrieve Memory → Generate Plan → Safety Check → Execute Steps → (On Failure: Retry → Escalate Tier 1 → Tier 2 → Tier 3) → Store Memory → Report User → Self-Improve

**Shutdown:** Stop accepting → Wait running (30s) → Save checkpoint → Close connections

Key behaviors:
- Local Qwen handles routine tasks; never calls cloud for simple work
- max_concurrent_tasks: 3  # configurable in agent.yaml
- LM Studio down → notify user, offer direct-tool access, fallback to rule-based dispatch
- State checkpointing every 30s + on shutdown
- Crash recovery: reload checkpoint, resume interrupted tasks
- Safety mode polling: agent checks safety_mode before each action
- Heartbeat: asyncio task that logs "agent alive" every 5s and updates `data/heartbeat.json` with timestamp + active task count. If heartbeat file is >15s stale, the UI shows a "LOST CONNECTION" banner.

**Planner JSON Contract — LLM must return this exact structure:**
```json
{"reasoning": "why this plan works", "confidence": 0.85, "steps": [{"description": "step text", "tool_name": "file_tool", "tool_args": {"path": "..."}, "depends_on": []}]}
```
Parse with `Plan.model_validate()`. On `ValidationError` → trigger the 3-retry JSON recovery defined in Section 16.

---

## 6. ESCALATION SYSTEM

### Triggers
| Condition | Threshold |
|-----------|-----------|
| Repeated step failure | 3 consecutive |
| Low confidence | < 0.4 |
| Code generation | >30 lines |
| Explicit request | "help" / "escalate" |
| Step timeout | >5 minutes |
| Context overflow | Window exceeded |

### Tier Details
- **Tier 1 (Copilot API):** CLI/API interface, 30s timeout, structured prompts
- **Tier 2 (Claude Code):** subprocess `claude --print`, 300s timeout, full repo access
- **Tier 3 (Cline in VS Code):** Claude Code opens VS Code + Cline, 600s timeout, long agentic sessions

### Circuit Breaker (per tier)
States: CLOSED → OPEN (after failures) → HALF_OPEN (after recovery)

---

## 7. TOOL SYSTEM (src/tools/)

### Base Contract:
```python
class BaseTool(ABC):
    name: str
    description: str
    risk_level: RiskLevel
    parameters_schema: dict
    async def execute(self, **kwargs) -> ToolResult
    async def validate_args(self, **kwargs) -> tuple[bool, str]
    def to_prompt_description(self) -> str
    def to_mcp_schema(self) -> dict
```

**BaseTool is the internal Python interface. to_mcp_schema() exposes it externally. Copilot must not create separate MCP tool classes — every tool is a BaseTool first, exposed via MCP server second. One implementation, two interfaces.**

### Requirements:
- Catch ALL exceptions internally, return `ToolResult(success=False, error=...)`
- Log every execution via loguru
- Record execution time in milliseconds
- Support dry-run mode
- Windows-compatible (`pathlib.Path`)

### Shell/Python Sandboxing:
- `shell_tool`: Whitelist commands. Default: `dir`, `type`, `findstr`, `echo`, `date`, `whoami`, `ping`. Timeout: 10s
- `python_tool`: Whitelist imports. Default: `json`, `re`, `datetime`, `math`, `os.path`, `pathlib`, `csv`. Timeout: 30s, Max memory: 256MB

### Tool Registry:
- Auto-discover from `tools/` directory on startup
- Runtime registration for self-improvement-generated tools
- Track usage statistics per tool

---

## 8. MEMORY SYSTEM (src/memory/)

| Type | Storage | Purpose | TTL |
|------|---------|---------|-----|
| Conversation | Ring buffer (50 msgs) | Session context | Session |
| Episodic | SQLite | Task history | 90 days |
| Semantic | ChromaDB | Searchable knowledge | 180 days |
| Procedural | SQLite + YAML | Learned workflows | Permanent |
| User Profile | JSON | Preferences | Permanent |

**Memory Manager:** Unified search ranking by relevance + recency + importance.

**Background Compaction (hourly):** Merge duplicates, decay old entries, promote frequently-accessed.

---

## 9. SAFETY SYSTEM (src/safety/)

### Risk Classification
| Level | Examples | Behavior |
|-------|---------|----------|
| SAFE | Read file, web search | Execute immediately |
| MODERATE | Email to known, create file | Explain, then execute |
| DANGEROUS | Delete, unknown email, shell | Require "yes" confirmation |
| FORBIDDEN | System files, registry, credentials | NEVER execute, log attempt |

### Safety Mode Control (UI Bottom-Left Panel)
```python
class SafetyMode(str, Enum):
    FULL = "full"           # All safety checks enforced
    LIGHT_BYPASS = "light_bypass"  # Skip light confirmations
    MEDIUM_BYPASS = "medium_bypass" # Skip light + medium confirmations
    SEVERE_LOCKED = "severe_locked" # Cannot be bypassed (CRITICAL)
```
- **Light Mode:** Toggle on/off - skips minor confirmation prompts
- **Medium Mode:** Toggle on/off - skips moderate warnings (NOT for system changes)
- **Severe Mode:** LOCKED ON - never bypassable (system files, full deletes, credentials)
- Critical safety rules ALWAYS enforced regardless of mode

### Audit Log
Append-only SQLite. Every action logged: timestamp, action, tool, risk level, user confirmation, input/output summary, success/failure.

### Rate Limits
- Email sends: max 5/hour
- File deletions: max 3/hour
- Shell commands: max 10/hour
- Escalations: max 30/day

---

## 10. SELF-IMPROVEMENT (src/self_improvement/)

DISABLED by default (`enable_self_improvement: false` in agent.yaml).

- **Failure Analyzer:** Classify failures. After 3+ identical, trigger escalation.
- **Workflow Learner:** Detect repeated patterns. After 3 identical, offer automation.
- **Tool Generator:** Escalate to Tier 2 to generate new tools.
- **Prompt Optimizer:** A/B test prompts. Require ≥10% improvement.

---

## 11. WEB UI - 4-QUADRANT DASHBOARD (src/interface/web_ui.py)

### Layout
4-quadrant browser dashboard. Top-left: live screenshot. Top-right: screenshot carousel with captions. Bottom-left: safety controls. Bottom-right: command interface.

### Top-Left: Live Screenshot (Real-time Desktop View)
- mss captures screenshot on each agent action (no browser required)
- Shows what agent is currently "seeing"
- Updates automatically after each tool execution
- Timestamp overlay showing capture time

### Top-Right: Screenshot Carousel (Action History)
- Horizontal carousel of past screenshots
- Each thumbnail has text explanation below:
  - "Opened File Explorer at C:\Users"
  - "Navigated to Downloads folder"
  - "Found document.pdf, 3.2MB"
- Click to enlarge
- Scrollable history (last 50 screenshots)

### Bottom-Left: Safety Controls Panel
- **Light Safety Toggle:** Skip minor confirmations (e.g., "Create new folder?")
- **Medium Safety Toggle:** Skip moderate warnings (e.g., "Send email to known contact?") - NOT for system changes
- **Severe Safety LOCKED:** Cannot be bypassed (red indicator)
  - System file modifications
  - Registry changes
  - Credential access
  - Full disk deletes

### Bottom-Right: Command Interface
- **Agent Thoughts Panel (Top):** Scrollable text showing agent's reasoning, concerns, status updates
- **Command Input (Middle):** Natural language input field for user commands
- **Common Commands (Bottom):** Scrollable list of quick-action buttons (preset commands)

### Technical Implementation
- FastAPI backend with WebSocket for real-time updates
- mss for screenshot capture (lightweight, no browser needed)
- HTMX for server-rendered dynamic updates
- `run_ui.bat` launches browser to `http://localhost:8000`
- Screenshots stored in `data/screenshots/`

---

## 12. CONFIGURATION FILES

### models.yaml
```yaml
local:
  primary:
    name: "huihui-qwen3.5-9b-abliterated-ties-i1"
    provider: "lmstudio"
    endpoint: "http://localhost:1234/v1"
    context_window: 32768
    token_budget:
      system_prompt: 8000
      memory_context: 8000
      conversation: 16000
escalation:
  tier1:
    provider: copilot_api
    base_url: "https://api.githubcopilot.com"
    model: gpt-4o
    auth: github_oauth_device_flow
    timeout_seconds: 30
  tier2:
    provider: claude_code_cli
    command: claude
    flags: ["--print", "--output-format", "json", "--max-turns", "10"]
    timeout_seconds: 300
  tier3:
    provider: claude_code_cli
    command: claude
    task: open_vscode_cline
    timeout_seconds: 600
```

### safety.yaml
```yaml
require_confirmation:
  - email_send
  - file_delete
  - shell_execute
  - browser_navigate_new_domain
rate_limits:
  email_send: {max: 5, period_hours: 1}
  file_delete: {max: 3, period_hours: 1}
  shell_execute: {max: 10, period_hours: 1}
  escalation_request: {max: 30, period_hours: 24}
forbidden_actions:
  - system_file_modification
  - registry_edit
  - credential_storage_access
  - unrestricted_shell_execution
sandbox:
  python:
    allowed_imports: [json, re, datetime, math, os.path, pathlib, csv]
    max_execution_seconds: 30
    max_memory_mb: 256
  shell:
    allowed_commands: [dir, type, findstr, echo, date, whoami, ping]
    max_execution_seconds: 10
safety_mode_default: "full"
```

### escalation.yaml
```yaml
triggers: {max_retries_before_escalate: 3, min_confidence_threshold: 0.4, max_step_timeout_seconds: 300}
routing: {code_generation: tier1, debugging: tier2, architecture: tier2, reasoning_depth: tier3}
fallback_chain: [tier1, tier2, tier3]
circuit_breaker: {failure_threshold: 3, recovery_timeout_seconds: 300}
```

### ui.yaml
```yaml
screenshot_interval_ms: 500
carousel_max_items: 50
websocket_ping_interval: 30
theme: "dark"
```

### memory.yaml
```yaml
semantic_memory_enabled: true  # Set to false if ChromaDB fails to install
semantic_search_timeout_seconds: 2.0
compaction_max_duration_seconds: 120
episodic_ttl_days: 90
semantic_max_entries: 10000
```

### agent.yaml
```yaml
max_concurrent_tasks: 3
task_queue_warn_threshold: 10
checkpoint_interval_seconds: 30
checkpoint_path: "data/checkpoint.json"
heartbeat_interval_seconds: 5
heartbeat_path: "data/heartbeat.json"
heartbeat_log: false
enable_self_improvement: false
self_improvement_threshold_hours: 24
self_improvement_threshold_tasks: 50
lmstudio_timeout_seconds: 120
lmstudio_retry_attempts: 3
pause_on_dangerous_action: false
```

### tools.yaml
```yaml
tools:
  file_tool: {enabled: true, dry_run_supported: true}
  web_search_tool: {enabled: true, dry_run_supported: true}
  email_tool: {enabled: true, dry_run_supported: true}
  python_tool: {enabled: true, dry_run_supported: true}
  shell_tool: {enabled: true, dry_run_supported: true}
  rag_tool: {enabled: true, dry_run_supported: true}
registry:
  auto_discover: true
  discovery_path: "src/tools"
  runtime_registration: true
```

### mcp.yaml
```yaml
server:
  host: "127.0.0.1"
  port: 8765
  auth_required: true
  auth_secret_env: MCP_AUTH_SECRET
rate_limits:
  per_client_calls: 60
  period_seconds: 60
tool_exposure:
  source: "BaseTool"
  require_to_mcp_schema: true
```

### pyproject.toml Key Settings
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
strict = true
```

---

## 13. BUILD ORDER (PHASES)

Each phase must be COMPLETE with passing tests before starting the next.

| Phase | Component | Key Deliverables |
|-------|-----------|------------------|
| 1 | Foundation | pyproject.toml, Pydantic models, config loader, loguru, CI |
| 2 | Tools Core | BaseTool, registry auto-discovery, to_mcp_schema(), file/shell/python/email/RAG stubs + tests |
| 3 | Screenshot | mss capture utility, data/screenshots/, thumbnail pipeline, tests |
| 4 | Model Integration | LM Studio client, health check, token counting, context management |
| 5 | Core Agent | Reasoner, planner, tool router, executor, executive loop, CLI |
| 6 | Memory | 5 memory types, unified manager, compaction, TTL |
| 7 | Safety | Action classifier, audit log, rate limiter, safety mode, FORBIDDEN enforcement |
| 8 | Escalation | Tier 1-3 clients, detector, manager, circuit breaker, solution applier |
| 9 | MCP Server | server.py, handlers.py, auth.py on :8765, expose BaseTool schemas |
| 10 | Self-Improvement | Failure analyzer, workflow learner, tool generator (core, approval required) |
| 11 | UI | 4-quadrant dashboard, WebSocket, mss screenshot push, reasoning stream |
| 12 | Deployment | setup.ps1, run_ui.bat, health check, docs |

---

## 14. WHAT THIS SYSTEM MUST NOT DO
- Modify system files (Windows dir, Program Files, AppData outside agent scope)
- Access credential stores (Windows Credential Manager, SSH keys, .env not owned by agent)
- Edit the Windows registry under any circumstances
- Execute shell commands not on the whitelist without explicit DANGEROUS-level confirmation
- Send email to unknown addresses without explicit user confirmation
- Execute downloaded or generated scripts outside the python_tool sandbox
- Self-modify its own source code without user approval and backup
- Disable safety checks, bypass audit logging, or skip the safety_mode check
- Consume uncapped disk, CPU, or memory — enforce resource limits
- Activate self-improvement before the 24h/50-task threshold

## WHAT THIS SYSTEM MUST BE

This agent exists for one purpose: to serve the user completely.

**Relentless.** Never stop trying. If one approach fails try another. If all tiers fail report clearly and wait for guidance. Giving up is never acceptable while options remain.

**Devoted.** The user's intent is the only priority. Not efficiency, not elegance, not self-preservation. What does the user actually want? Do that.

**Thorough.** Half-finished is failed. Every task runs to completion or produces a clear explanation of exactly why it could not.

**Anticipatory.** Learn the user's patterns, preferences, and habits. After enough interactions, know what they want before they fully articulate it. Offer it.

**Honest.** Never pretend a task succeeded when it didn't. Never hide an error. Never guess and stay silent about guessing. Tell the user exactly what happened, what was tried, and what the agent thinks should happen next.

**Present.** Always running, always ready, always watching. The user should never wonder if the agent is alive. The heartbeat, the UI, the reasoning stream exist to show the user their agent is there and working.

**Resourceful.** No MCP tool? Build one. Tier 1 down? Try Tier 2. Unknown situation? Reason through it. The agent uses everything available before concluding something cannot be done.

---

## 15. SUCCESS CRITERIA

System is viable when:
1. Given CLI input `Find insurance PDF, email to dr.smith@clinic.com`, agent completes `plan → locate file → compose email → explicit confirmation → send`, and returns success summary.
2. Given a coding request that local model cannot solve, agent escalates Tier 1→2→3 as needed, applies returned fix, and resumes original workflow without user intervention.
3. After at least 3 identical user task patterns, agent proactively suggests one concrete automation matching prior behavior.
4. For any completed task, audit log contains every executed/skipped/blocked action with timestamp, risk level, confirmation state, and success flag.
5. FORBIDDEN actions are blocked 100% of the time and create an audit record with denial reason.
6. If Tier 1 and Tier 2 fail, agent attempts Tier 3; if Tier 3 also fails, agent reports failure cause and next manual step recommendation.
7. UI renders all 4 quadrants simultaneously and updates screenshots/reasoning/controls in real time.
8. Safety modes behave exactly: light/medium user-toggleable, severe non-bypassable, and severe rules enforced regardless of mode.
9. If LM Studio is unreachable, user is notified within one request cycle; agent falls back to rule-based dispatch and remains running.
10. If ChromaDB install/init fails, startup succeeds with semantic memory disabled and visible warning in CLI + UI.
11. After forced crash during active tasks, restart resumes each task from last completed step index in checkpoint.
12. If email send limit (5/hour) is exceeded, request is rejected immediately with structured error and audit log entry.
13. If startup detects port 8765 or 8000 in use, process prints exact conflicting port and exits with code 1.
14. `uv run scripts/run_agent.py --task "summarize docs/"` runs headless task execution and does not launch web UI.
15. MCP server accepts authenticated tool calls from Claude Code and rejects invalid tokens with explicit auth error.
16. Background compaction always completes or cancels within 120 seconds and never blocks step execution.
17. On WebSocket disconnect/reconnect, agent continues task execution and client receives full current state immediately after reconnect.
18. When self-improvement generates a tool, file is written to `src/mcp_tools/`, `mcp.yaml` is updated, and user is told restart is required.

---

## 16. IMPLEMENTATION REQUIREMENTS

### health_check.py (scripts/health_check.py)
On startup run: `subprocess.run(["claude", "--help"], capture_output=True)`. Parse the output and verify `--output-format` and `--print` flags exist. If either is missing, print exact error: "Claude Code CLI flags have changed. Check escalation/tier2_claude_code.py" and disable Tier 2 escalation rather than failing silently.

### executor.py (src/core/executor.py)
Screenshot capture runs in a separate asyncio task using `asyncio.create_task()`. The executor does not await it. Tool execution continues immediately after dispatch. If screenshot task fails for any reason it is silently discarded — never blocks or raises.

### web_ui.py (src/interface/web_ui.py)
All WebSocket sends use `asyncio.create_task(ws.send())`. The agent never awaits WebSocket sends. If the WebSocket is disconnected the send task fails silently and is discarded. Agent state and execution are completely independent of UI connection status.

### memory/manager.py (src/memory/manager.py)
Background compaction runs in a dedicated asyncio task started on agent startup. It never runs on the main event loop. Use `asyncio.create_task()` with a 60-minute sleep loop. If compaction takes more than 120 seconds, cancel it and log a warning. Never block the main loop.

### memory/semantic.py (src/memory/semantic.py)
Wrap every ChromaDB query in `asyncio.wait_for()` with `timeout=2.0` seconds. On timeout log a warning "semantic search timed out, skipping" and return empty results. The planner continues with conversation and episodic memory only. Never let a slow ChromaDB query delay task execution.

### setup.ps1 (scripts/setup.ps1)
Install ChromaDB with: `pip install chromadb --prefer-binary`
If that fails, try: `pip install chromadb --no-build-isolation`
If that fails, disable semantic memory, set `semantic_memory_enabled: false` in memory.yaml, print warning to user, continue setup. Agent must start even if ChromaDB fails to install.

### LM Studio Client (src/core/reasoner.py or src/utils/lm_studio_client.py)
After every completion request, attempt to parse the response into the expected Pydantic model. If parsing fails, retry the request up to 3 times with a note appended to the prompt: "Respond with valid JSON only. Previous response could not be parsed."
If all 3 retries fail, return a failed PlanStep with error="local model returned unparseable response" and escalate to Tier 1. Never let a bad JSON response crash the executor.

### Tool Building (src/self_improvement/tool_generator.py)
When a new MCP tool is built by Claude Code, write the file to `src/mcp_tools/`, update `mcp.yaml`, then notify the user: "New tool [name] built. Restart agent to load it." Do not attempt runtime hot-reload. No `importlib.reload()`. No watchdog on tools directory.

### Self-Improvement Activation Threshold
Self-improvement only activates after 24 hours of runtime or 50 completed tasks, whichever comes first. Before that threshold all self-improvement modules run in observe-only mode — they collect data but take no action.

### Circuit Breaker Task Routing
While a tier's circuit breaker is OPEN, any task that would have used that tier skips immediately to the next tier in the fallback chain. Tasks do not queue waiting for circuit breaker recovery.

### Copilot Token Refresh
On every Tier 1 call, check if the Copilot token is within 24 hours of expiry. If so, refresh it automatically using the stored refresh token. If refresh fails, disable Tier 1, log the error, fall through to Tier 2.

### Claude Code Turn Limit Handling
Parse Claude Code JSON output for a completion indicator. If max turns is hit without completion, treat the response as a failure, log "Claude Code hit turn limit without resolution" and escalate to Tier 3. Never apply a partial Claude Code result.

### MCP Server Rate Limits
MCP server enforces rate limits per calling process: max 60 tool calls per minute per connected client. On limit exceeded return error immediately, do not queue. This is separate from the user-facing rate limits in safety.yaml.

### Pause Behavior
Pause means: finish the currently executing step, then stop. Do not abandon mid-step. Queued tasks remain in queue. User sees "Paused after current step completes" in the UI. Resume picks up from next queued task.

### Screenshot Carousel Storage
Screenshots sent to carousel are resized to 400px wide thumbnails using Pillow before storage. Full resolution originals stay on disk in data/screenshots/. Carousel holds thumbnails only. Click-to-enlarge fetches from disk on demand.

### Checkpoint Format
Checkpoint saves to data/checkpoint.json and contains: active task list with current step index, task queue, current safety mode, circuit breaker states per tier, memory session ring buffer. On crash recovery load checkpoint.json, resume each active task from its last completed step index.

### Node.js Version Requirement
setup.ps1 checks Node.js version before installing any npm packages. Minimum required: Node 18.0.0. If below 18, print error with download link https://nodejs.org and exit. Do not attempt npm installs on unsupported Node versions.

### Task Queue Overflow
If max_concurrent_tasks is reached, new requests are added to a FIFO queue displayed in the UI. User is immediately notified: "Task queued, currently running N tasks." Queue has no hard limit but agent warns user when queue exceeds 10 items.

### LM Studio Timeout
LM Studio requests have a configurable timeout defaulting to 120 seconds in `agent.yaml` (`lmstudio_timeout_seconds`). On timeout do not retry — Qwen is busy or overloaded. Return a failed plan with error="local model timeout" and escalate directly to Tier 1. Log the timeout duration.

### WebSocket Reconnect State
On WebSocket reconnect, server immediately pushes current full state: active task, last 10 carousel items, current safety mode, current reasoning buffer last 100 lines, task queue. UI never shows stale or empty state after reconnect.

### Memory Cleanup
Implement automatic cleanup of old memory entries. Episodic memory: delete entries older than 90 days. Semantic memory: delete entries older than 180 days and cap retained entries to top 10,000 by relevance score.

### Escalation Full-Failure Behavior
If all three tiers fail, mark current step as `FAILED`, mark task as `ESCALATED` with terminal failure status, persist failure details in audit log and checkpoint, and return a structured user message:
`All escalation tiers failed. Last error: <error>. Recommended next action: <manual step>.`
Agent must remain running for subsequent tasks.

### Checkpoint Corruption Recovery
On startup, if `data/checkpoint.json` exists but fails JSON parse or schema validation:
1. Move it to `data/checkpoint.corrupt.<timestamp>.json`
2. Log an error with parse/validation details
3. Start with empty runtime state
4. Notify user in CLI and UI that recovery used a clean checkpoint
Never crash startup due to corrupted checkpoint.

### CLI Invocation Contract
`scripts/run_agent.py` must support:
- Interactive mode: `uv run scripts/run_agent.py`
- One-shot mode: `uv run scripts/run_agent.py --task "<text>"`
- Headless flag: `uv run scripts/run_agent.py --task "<text>" --no-ui`
`--task` executes one request in headless mode by default and exits with code 0 on success, code 1 on failure.

### Idle vs Paused State Signaling
- **Idle:** no running task and queue empty; UI status badge = `IDLE` (green)
- **Paused:** pause command issued; current step allowed to finish; queue processing halted; UI status badge = `PAUSED` (yellow)
- Transition to `PAUSED` occurs only after current step finishes.
- Transition from `PAUSED` to `IDLE/RUNNING` occurs only on explicit resume command.

### Screenshot Retention Policy
- Store full-resolution screenshots under `data/screenshots/full/`
- Store 400px thumbnails under `data/screenshots/thumbs/`
- Keep last 50 thumbnails for carousel
- Delete full-resolution screenshots older than 7 days during daily cleanup
- Total screenshot disk budget: 2GB; on exceed, delete oldest full-resolution files first

### Tool Discovery
On startup, scan `src/tools/` directory for BaseTool subclasses. Import and register each tool. Log registration success/failure.

### Configuration Validation
On startup, validate all YAML config files against Pydantic models. Check required fields and type compatibility. Exit with clear error messages if validation fails.

### Health Monitoring
Implement `/health` endpoint returning system status: LM Studio connection, ChromaDB status, disk space, memory usage.
