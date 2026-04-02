# Architecture Overview

## Async Execution Flow

```
User Input (CLI / WebSocket)
        │
        ▼
  ExecutiveAgent.process(text)
        │
        ├─ [PLANNING] LocalPlanner.generate(UserRequest)
        │       │
        │       └─ LM-Studio API (POST /v1/chat/completions)
        │              └─ Serialised by asyncio.Semaphore(1) [VRAM guardrail]
        │
        ├─ [RUNNING] iterate over Plan.steps
        │       │
        │       ├─ SafetyClassifier.classify(tool, args) → RiskLevel
        │       ├─ RateLimiter.allow(tool) → bool
        │       ├─ [MODERATE/DANGEROUS] ConfirmationProtocol.ask() → bool
        │       │
        │       └─ ToolRouter.dispatch(step)
        │               │
        │               ├─ TOOL_REGISTRY lookup
        │               ├─ BaseTool.validate(**args)
        │               ├─ BaseTool.execute(**args)  [with tenacity retry x3]
        │               └─ metrics.inc(tool_executions_<name>)
        │
        ├─ [on failure] EscalationManager.initiate(EscalationRequest)
        │       │
        │       ├─ CircuitBreaker check per tier
        │       ├─ Tier 1: tier1_vscode.run()  (VS Code / Cline)
        │       ├─ Tier 2: tier2_claude.run()  (Claude API)
        │       └─ Tier 3: tier3_browser.run() (Playwright browser)
        │
        ├─ [after each step] AuditLog.log(AuditEntry) → SQLite
        │
        └─ [on completion] Task.status = COMPLETED / FAILED / ESCALATED
```

## Component Map

| Module | Responsibility |
|--------|---------------|
| `src/core/models.py` | Pydantic v2 data model definitions |
| `src/core/planner.py` | LM-Studio async planner |
| `src/core/executive.py` | Main async state machine |
| `src/core/tool_router.py` | Tool dispatch + tenacity retry |
| `src/tools/` | Tool implementations (file, shell, python, web, email, browser) |
| `src/tools/registry.py` | Auto-discovery of BaseTool subclasses |
| `src/safety/` | Classifier, rate limiter, sandbox, audit log, confirmation |
| `src/escalation/` | EscalationManager + tier mocks |
| `src/memory/manager.py` | Conversation ring-buffer + SQLite + ChromaDB |
| `src/utils/` | Config loader, token window, JSON logging, SQLite metrics |
| `src/interface/cli.py` | Rich interactive CLI |
| `src/interface/web_ui.py` | FastAPI REST + WebSocket UI |
| `scripts/run_agent.py` | Entry-point script |
| `config/*.yaml` | Runtime configuration |

## Key Design Decisions

- **Single LLM semaphore** – `asyncio.Semaphore(1)` prevents concurrent VRAM usage.
- **Modular tools** – each tool is a `BaseTool` subclass; auto-discovered via `importlib`.
- **Safety-first** – classify → rate-limit → confirm before any tool execution.
- **Lightweight observability** – `loguru` JSON logs + SQLite `metrics` table (no OpenTelemetry yet; see ADR-001).
- **Mock-first escalation** – all external tier calls return static payloads until real integrations are wired in.
