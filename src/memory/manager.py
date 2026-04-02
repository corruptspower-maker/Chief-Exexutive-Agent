"""Unified memory manager combining conversation, SQLite, and ChromaDB."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.models import MemoryEntry
from src.utils.logging import json_log

_MAX_CONV = 50
_SQL_DB = Path("memory.db")
_COMPACT_INTERVAL = 3600  # 1 hour in seconds


class MemoryManager:
    """Unified memory subsystem with conversation ring-buffer, SQLite, and ChromaDB.

    Attributes:
        conv: Ring-buffer of recent conversation strings (max 50).
        sql: SQLite connection for procedural memory.
    """

    def __init__(self) -> None:
        self.conv: deque[dict[str, Any]] = deque(maxlen=_MAX_CONV)
        self.sql = sqlite3.connect(str(_SQL_DB), check_same_thread=False)
        self._init_sql()
        self._chroma_collection: Any | None = self._init_chroma()
        self._compact_task: asyncio.Task[None] | None = None

    def _init_sql(self) -> None:
        """Create the procedural memory table if it does not exist.

        Returns:
            None
        """
        self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS procedural (
                id          TEXT PRIMARY KEY,
                content     TEXT NOT NULL,
                embedding_id TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                tags        TEXT NOT NULL
            )
            """
        )
        self.sql.execute("PRAGMA journal_mode=WAL")
        self.sql.commit()

    def _init_chroma(self) -> Any | None:
        """Initialise a CPU-only ChromaDB collection.

        Returns:
            ChromaDB collection or None if unavailable.
        """
        try:
            import chromadb  # local import to avoid hard dependency at module load

            client = chromadb.Client()
            return client.get_or_create_collection("memory")
        except Exception:
            json_log("chroma_unavailable")
            return None

    def start_background_tasks(self) -> None:
        """Schedule the background compaction task.

        Should be called after an event loop is running.

        Returns:
            None
        """
        self._compact_task = asyncio.create_task(self._compact())

    async def add_conversation(self, entry: str) -> None:
        """Append a string to the conversation ring-buffer.

        Args:
            entry: Conversation string to store.

        Returns:
            None
        """
        self.conv.append({"text": entry, "ts": datetime.now(timezone.utc).isoformat()})

    async def query_semantic(self, text: str, top_k: int = 5) -> list[MemoryEntry]:
        """Query ChromaDB for semantically similar entries.

        Args:
            text: Query text.
            top_k: Maximum number of results to return.

        Returns:
            List of MemoryEntry objects ranked by similarity.
        """
        if self._chroma_collection is None:
            return []
        try:
            results = self._chroma_collection.query(query_texts=[text], n_results=top_k)
            entries: list[MemoryEntry] = []
            for doc_id, doc in zip(
                results["ids"][0], results["documents"][0], strict=False
            ):
                entries.append(MemoryEntry(id=doc_id, content=doc, embedding_id=doc_id))
            return entries
        except Exception as exc:
            json_log("semantic_query_failed", error=str(exc))
            return []

    async def store_procedural(self, entry: MemoryEntry) -> None:
        """Persist a MemoryEntry to SQLite and ChromaDB.

        Args:
            entry: The MemoryEntry to store.

        Returns:
            None
        """
        self.sql.execute(
            "INSERT OR REPLACE INTO procedural (id, content, embedding_id, created_at, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.content,
                entry.embedding_id,
                entry.created_at.isoformat(),
                json.dumps(entry.tags),
            ),
        )
        self.sql.commit()
        if self._chroma_collection is not None:
            try:
                self._chroma_collection.upsert(
                    ids=[entry.id],
                    documents=[entry.content],
                )
            except Exception as exc:
                json_log("chroma_upsert_failed", error=str(exc))

    async def _compact(self) -> None:
        """Background task: compact old conversation entries every hour.

        Returns:
            None
        """
        while True:
            await asyncio.sleep(_COMPACT_INTERVAL)
            json_log("memory_compact", conv_size=len(self.conv))


if __name__ == "__main__":
    print("Run `uv run scripts/run_agent.py`")
