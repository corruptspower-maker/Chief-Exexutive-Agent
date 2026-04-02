"""FastAPI web interface for Chief Executive Agent."""
from __future__ import annotations

import asyncio
import psutil
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from src.utils import metrics

app = FastAPI(title="Chief Executive Agent", version="0.1.0")

_task_subscribers: list[WebSocket] = []


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
