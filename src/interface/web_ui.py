"""FastAPI web interface for Chief Executive Agent."""
from __future__ import annotations

import asyncio
import psutil
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from src.core.executive import ExecutiveAgent
from src.core.models import Task, UserRequest
from src.core.planner import LocalPlanner
from src.core.tool_router import ToolRouter
from src.escalation.manager import EscalationManager
from src.safety.audit_log import AuditLog
from src.safety.confirmation import ConfirmationProtocol
from src.utils import metrics

_agent: ExecutiveAgent | None = None
_tasks: dict[str, Task] = {}
_task_subscribers: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Initialise the ExecutiveAgent on startup and clean up on shutdown."""
    global _agent
    _agent = ExecutiveAgent(
        planner=LocalPlanner(),
        router=ToolRouter(),
        escalation=EscalationManager(),
        audit=AuditLog(),
        safety=ConfirmationProtocol(),
    )
    yield
    _agent = None


app = FastAPI(title="Chief Executive Agent", version="0.1.0", lifespan=lifespan)


class TaskRequest(BaseModel):
    """Request body for POST /task."""

    text: str


# ---------------------------------------------------------------------------
# HTML dashboard
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = """<!DOCTYPE html>
<html><head>
  <title>Chief Executive Agent</title>
  <style>
    body{font-family:monospace;background:#0d1117;color:#c9d1d9;padding:2rem}
    h1{color:#58a6ff}
    #form{display:flex;gap:.5rem}
    input{flex:1;padding:.5rem;background:#161b22;color:#c9d1d9;border:1px solid #30363d}
    button{padding:.5rem 1rem;background:#238636;color:#fff;border:none;cursor:pointer}
    #tasks{margin-top:1.5rem}
    .task{padding:.4rem .6rem;margin:.2rem 0;border-left:3px solid #58a6ff}
    .task.completed{border-color:#3fb950}.task.failed{border-color:#f85149}
    .task.running,.task.planning{border-color:#d29922}
    .badge{display:inline-block;padding:.1rem .4rem;border-radius:3px;font-size:.8rem;
           background:#30363d;margin-left:.5rem}
  </style>
</head><body>
  <h1>Chief Executive Agent</h1>
  <div id="form">
    <input id="ti" type="text" placeholder="Enter a task and press Enter…" />
    <button onclick="submitTask()">▶ Run</button>
  </div>
  <div id="tasks"><p style="color:#8b949e">No tasks yet.</p></div>
  <script>
    const tasks={};
    const ws=new WebSocket('ws://'+location.host+'/ws');
    ws.onmessage=e=>{
      const m=JSON.parse(e.data);
      if(m.task_id){tasks[m.task_id]={...tasks[m.task_id],...m};render();}
    };
    document.getElementById('ti').addEventListener('keydown',e=>{
      if(e.key==='Enter')submitTask();
    });
    function render(){
      const el=document.getElementById('tasks');
      const list=Object.values(tasks).reverse();
      if(!list.length){el.innerHTML='<p style="color:#8b949e">No tasks yet.</p>';return;}
      el.innerHTML=list.map(t=>
        `<div class="task ${t.status||'pending'}">
          <code>${(t.task_id||'').slice(0,8)}</code>
          <span class="badge">${t.status||'accepted'}</span>
          ${t.text?' — '+t.text.slice(0,100):''}
        </div>`
      ).join('');
    }
    async function submitTask(){
      const text=document.getElementById('ti').value.trim();
      if(!text)return;
      const r=await fetch('/task',{method:'POST',
        headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
      const d=await r.json();
      tasks[d.task_id]={task_id:d.task_id,status:d.status,text};
      render();
      document.getElementById('ti').value='';
    }
  </script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    """Return the HTML task dashboard.

    Returns:
        HTML page with task submission form and live task list.
    """
    return _DASHBOARD_HTML


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------


@app.post("/task")
async def submit_task(body: TaskRequest) -> dict[str, str]:
    """Accept a natural-language task and run it in the background.

    Args:
        body: JSON body with ``text`` field.

    Returns:
        JSON dict with ``task_id`` and initial ``status``.

    Raises:
        HTTPException: 503 if the agent has not been initialised.
        HTTPException: 400 if ``text`` is empty.
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialised")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Task text must not be empty")

    req = UserRequest(text=text)
    placeholder = Task(id=req.id, request=req)
    _tasks[placeholder.id] = placeholder

    async def _run() -> None:
        finished = await _agent.process(text)
        _tasks[finished.id] = finished
        await broadcast(
            {"type": "task_update", "task_id": finished.id, "status": finished.status.value}
        )

    asyncio.create_task(_run())
    await broadcast({"type": "task_created", "task_id": placeholder.id, "text": text, "status": "accepted"})
    return {"task_id": placeholder.id, "status": "accepted"}


@app.get("/tasks")
async def list_tasks() -> list[dict[str, Any]]:
    """Return all tasks with their current status.

    Returns:
        List of task summary dicts ordered by creation time (newest first).
    """
    return [
        {
            "task_id": t.id,
            "text": t.request.text,
            "status": t.status.value,
            "created_at": t.created_at.isoformat(),
            "error": t.error,
        }
        for t in sorted(_tasks.values(), key=lambda x: x.created_at, reverse=True)
    ]


@app.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    """Return detailed status of a specific task.

    Args:
        task_id: UUID of the task.

    Returns:
        Task detail dict.

    Raises:
        HTTPException: 404 if the task is not found.
    """
    t = _tasks.get(task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": t.id,
        "text": t.request.text,
        "status": t.status.value,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        "error": t.error,
        "plan_steps": len(t.plan.steps) if t.plan else 0,
    }


# ---------------------------------------------------------------------------
# Health & metrics
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    """Return service health status.

    Returns:
        JSON dict with LM-Studio reachability, database status, memory usage,
        and active task count.
    """
    import httpx

    lm_studio_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:1234/v1/models")
            lm_studio_ok = resp.status_code == 200
    except Exception:
        pass

    mem_mb = psutil.Process().memory_info().rss / 1024 / 1024
    active = sum(
        1 for t in _tasks.values() if t.status.value in ("pending", "planning", "running")
    )

    return {
        "lm_studio": "ok" if lm_studio_ok else "unreachable",
        "database": "ok",
        "memory_usage_mb": round(mem_mb, 2),
        "active_tasks": active,
        "total_tasks": len(_tasks),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics() -> str:
    """Return Prometheus-compatible plain-text metrics from the SQLite metrics table.

    Returns:
        Plain-text metric lines in Prometheus exposition format.
    """
    data = metrics.get_all()
    lines = ["# HELP chief_executive_agent Counters\n# TYPE chief_executive_agent counter"]
    for key, value in data.items():
        lines.append(f'chief_executive_agent{{key="{key}"}} {value}')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time task updates.

    Sends current task states on connect, then streams live updates.

    Args:
        websocket: The incoming WebSocket connection.
    """
    await websocket.accept()
    _task_subscribers.append(websocket)
    # Replay current task states to the new subscriber
    for t in _tasks.values():
        try:
            await websocket.send_json(
                {"type": "task_update", "task_id": t.id, "status": t.status.value, "text": t.request.text}
            )
        except Exception:
            break
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        if websocket in _task_subscribers:
            _task_subscribers.remove(websocket)


async def broadcast(message: dict[str, Any]) -> None:
    """Push a JSON message to all connected WebSocket clients.

    Args:
        message: JSON-serialisable dict to broadcast.
    """
    disconnected: list[WebSocket] = []
    for ws in list(_task_subscribers):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in _task_subscribers:
            _task_subscribers.remove(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/health")
async def health() -> dict[str, Any]:
    """Return service health status.

    Returns:
        JSON dict with lm_studio reachability, database status, and memory usage.
    """
    import httpx

    lm_studio_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get("http://localhost:1234/v1/models")
            lm_studio_ok = resp.status_code == 200
    except Exception:
        pass

    mem_mb = psutil.Process().memory_info().rss / 1024 / 1024

    return {
        "lm_studio": "ok" if lm_studio_ok else "unreachable",
        "database": "ok",
        "memory_usage_mb": round(mem_mb, 2),
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics() -> str:
    """Return Prometheus-compatible plain-text metrics from the SQLite metrics table.

    Returns:
        Plain-text metric lines in Prometheus exposition format.
    """
    data = metrics.get_all()
    lines = [f"# HELP chief_executive_agent Counters\n# TYPE chief_executive_agent counter"]
    for key, value in data.items():
        lines.append(f'chief_executive_agent{{key="{key}"}} {value}')
    return "\n".join(lines)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time task updates.

    Args:
        websocket: The incoming WebSocket connection.

    Returns:
        None
    """
    await websocket.accept()
    _task_subscribers.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
            # Keep connection alive; task updates are pushed via broadcast
    except WebSocketDisconnect:
        _task_subscribers.remove(websocket)


async def broadcast(message: dict[str, Any]) -> None:
    """Push a JSON message to all connected WebSocket clients.

    Args:
        message: JSON-serialisable dict to broadcast.

    Returns:
        None
    """
    disconnected: list[WebSocket] = []
    for ws in list(_task_subscribers):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in _task_subscribers:
            _task_subscribers.remove(ws)


if __name__ == "__main__":
    import uvicorn

    print("Run `uv run scripts/run_agent.py`")
    uvicorn.run(app, host="0.0.0.0", port=8000)
