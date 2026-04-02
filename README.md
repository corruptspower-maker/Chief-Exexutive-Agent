# Chief Executive Agent

A self-improving AI operator that runs locally, does real tasks on your computer, and calls in the big models only when it needs help.

## Quick Start

### 1. Prerequisites
- Python 3.11 or later
- [uv](https://github.com/astral-sh/uv) package manager
- [LM-Studio](https://lmstudio.ai/) running locally on `http://localhost:1234`
- Google Chrome (for Tier-3 browser escalation)

### 2. Setup

```powershell
# Windows – run the bootstrap script
.\scripts\setup.ps1
```

This will:
- Install all Python dependencies via `uv`
- Install Playwright Chromium
- Create Chrome profiles for Tier-3 escalation
- Copy `.env.example` → `.env`

### 3. Configure

Edit `.env` with your secrets (SMTP credentials, LM-Studio model name, etc.).

### 4. Start LM-Studio

Launch LM-Studio and load your preferred model. The agent calls `http://localhost:1234/v1/chat/completions`.

### 5. Run

```bash
uv run scripts/run_agent.py
```

Type a request at the `>>> ` prompt. Type `exit` or `quit` to stop.

---

## Supported Tools

| Tool | Risk | Description |
|------|------|-------------|
| `file_tool` | SAFE | Read/write files inside `user_data/` |
| `web_search_tool` | SAFE | Web search (mocked; swap URL for real API) |
| `shell_tool` | DANGEROUS | Run whitelisted shell commands |
| `python_tool` | DANGEROUS | Execute sandboxed Python code |
| `email_tool` | MODERATE | Compose and send emails (requires confirmation) |
| `browser_tool` | DANGEROUS | Browser automation via Playwright (Tier-3 only) |

---

## Escalation Tiers

| Tier | Target | Latency |
|------|--------|---------|
| 1 | VS Code / Cline | < 1 s (mock) |
| 2 | Claude API | ~2 s (mock) |
| 3 | Browser (ChatGPT/Claude.ai) | ~5 s (mock) |

---

## Web UI

```bash
uv run uvicorn src.interface.web_ui:app --reload
```

- `GET /health` – service health
- `GET /metrics` – Prometheus-compatible counters
- `WS /ws` – real-time task updates

---

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Lint
uv run ruff check .

# Type-check
uv run mypy src/

# Tests
uv run pytest
```

---

## Safety

- All shell commands are validated against a whitelist in `config/safety.yaml`
- Python code is sandboxed and forbidden imports are blocked via `ast.parse`
- High-risk actions require explicit user confirmation before execution
- LLM calls are serialised by a semaphore to prevent VRAM exhaustion
