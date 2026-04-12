"""持久化模块。

把历史根目录 ``persistence.py`` 的实现迁入包内，供新的包路径直接引用；
根目录同名文件仅保留兼容转发能力。
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable, TypeVar

import aiosqlite

from nocode_agent.runtime.paths import default_checkpoint_db_path, resolve_runtime_path

logger = logging.getLogger(__name__)
_T = TypeVar("_T")
_SQLITE_CORRUPTION_MARKERS = (
    "database disk image is malformed",
    "disk image is malformed",
    "file is not a database",
    "database corrupt",
)


def _import_sqlite_saver():
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        return AsyncSqliteSaver
    except ImportError:
        raise RuntimeError(
            "missing LangGraph SQLite async checkpointer support. Install the langgraph SQLite checkpoint package first."
        )


def _iter_exception_chain(error: BaseException):
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _is_sqlite_corruption_error(error: BaseException) -> bool:
    for item in _iter_exception_chain(error):
        message = str(item).strip().lower()
        if any(marker in message for marker in _SQLITE_CORRUPTION_MARKERS):
            return True
    return False


def _build_corrupt_backup_path(db_path: Path, stamp: str, trailer: str) -> Path:
    candidate = Path(f"{db_path}.corrupt-{stamp}{trailer}")
    index = 1
    while candidate.exists():
        candidate = Path(f"{db_path}.corrupt-{stamp}-{index}{trailer}")
        index += 1
    return candidate


def _archive_corrupted_checkpoint_files(db_path: Path) -> list[Path]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archived: list[Path] = []
    for trailer in ("", "-wal", "-shm"):
        source = Path(f"{db_path}{trailer}")
        if not source.exists():
            continue
        target = _build_corrupt_backup_path(db_path, stamp, trailer)
        source.replace(target)
        archived.append(target)
    return archived


def _log_corruption_recovery(
    db_path: Path,
    error: BaseException,
    operation: str,
    archived: list[Path],
) -> None:
    archived_label = ", ".join(str(path) for path in archived) if archived else "(none)"
    logger.warning(
        "Checkpoint DB corrupted during %s: %s; db=%s; archived=%s",
        operation,
        error,
        db_path,
        archived_label,
    )


def _recover_corrupted_checkpoint_db_sync(
    db_path: Path,
    error: BaseException,
    operation: str,
) -> None:
    archived = _archive_corrupted_checkpoint_files(db_path)
    _log_corruption_recovery(db_path, error, operation, archived)


def _check_sqlite_health(db_path: Path) -> None:
    if not db_path.exists():
        return

    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(str(db_path))
        row = db.execute("PRAGMA quick_check(1)").fetchone()
        if not row:
            return
        status = str(row[0]).strip()
        if status.lower() != "ok":
            raise sqlite3.DatabaseError(f"database disk image is malformed: {status}")
    finally:
        if db is not None:
            db.close()


def _run_sqlite_read(
    db_path: str,
    operation: str,
    fallback: _T,
    callback: Callable[[sqlite3.Connection], _T],
) -> _T:
    resolved = Path(db_path).expanduser()
    if not resolved.exists():
        return fallback

    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(str(resolved))
        return callback(db)
    except Exception as error:
        if db is not None:
            db.close()
            db = None
        if _is_sqlite_corruption_error(error):
            _recover_corrupted_checkpoint_db_sync(resolved, error, operation)
            return fallback
        raise
    finally:
        if db is not None:
            db.close()


class CheckpointerManager:
    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path).expanduser()
        self._connection: aiosqlite.Connection | None = None
        self._saver = None
        self._setup_lock: asyncio.Lock | None = None
        self._setup_done = False
        self._lock = Lock()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def get(self):
        with self._lock:
            if self._saver is None or self._connection is None:
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
                connection = aiosqlite.connect(str(self._db_path))
                AsyncSqliteSaver = _import_sqlite_saver()
                self._connection = connection
                self._saver = AsyncSqliteSaver(connection)
            return self._saver

    async def _reset_saver(self) -> None:
        with self._lock:
            connection = self._connection
            self._connection = None
            self._saver = None
            self._setup_done = False
        if connection is not None:
            try:
                await connection.close()
            except Exception as error:
                logger.warning("Failed to close checkpoint connection: %s", error)

    async def _recover_corrupted_checkpoint_db(
        self,
        error: BaseException,
        operation: str,
    ) -> None:
        await self._reset_saver()
        archived = _archive_corrupted_checkpoint_files(self._db_path)
        _log_corruption_recovery(self._db_path, error, operation, archived)

    async def ensure_setup(self) -> None:
        if self._setup_done:
            return
        if self._setup_lock is None:
            self._setup_lock = asyncio.Lock()
        async with self._setup_lock:
            if self._setup_done:
                return
            try:
                _check_sqlite_health(self._db_path)
            except Exception as error:
                if not _is_sqlite_corruption_error(error):
                    raise
                await self._recover_corrupted_checkpoint_db(error, "quick_check")
            saver = self.get()
            try:
                await saver.setup()
            except Exception as error:
                if not _is_sqlite_corruption_error(error):
                    raise
                await self._recover_corrupted_checkpoint_db(error, "setup")
                saver = self.get()
                await saver.setup()
            self._setup_done = True
            logger.info("Checkpointer setup complete: %s", self._db_path)

    async def delete_thread(self, thread_id: str) -> None:
        logger.info("Deleting thread: %s", thread_id)
        await self.ensure_setup()
        saver = self.get()
        delete_thread = getattr(saver, "adelete_thread", None)
        if not callable(delete_thread):
            raise RuntimeError("configured checkpointer does not support delete_thread")
        try:
            await delete_thread(thread_id)
        except Exception as error:
            if not _is_sqlite_corruption_error(error):
                raise
            await self._recover_corrupted_checkpoint_db(error, "delete_thread")
            await self.ensure_setup()


def resolve_checkpoint_path(config: dict[str, Any] | None = None) -> str:
    resolved = ""
    if config:
        resolved = str(config.get("checkpoint_db_path", "") or "")
    if not resolved:
        resolved = str(default_checkpoint_db_path())
    return str(resolve_runtime_path(resolved))


def list_threads(
    db_path: str,
    limit: int = 50,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """List threads from the checkpoint DB with metadata.

    Returns a list of dicts with keys: thread_id, preview, message_count, source.
    Ordered by most recent first.
    Filter by source ("tui" or "multiagent") if provided.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    def _load(db: sqlite3.Connection) -> list[dict[str, Any]]:
        saver = SqliteSaver(db)
        saver.setup()

        rows = db.execute(
            "SELECT DISTINCT thread_id FROM checkpoints "
            'WHERE checkpoint_ns = "" ORDER BY rowid DESC LIMIT ?',
            (limit,),
        ).fetchall()
        if not rows:
            return []

        results: list[dict[str, Any]] = []
        for (thread_id,) in rows:
            try:
                state = saver.get({"configurable": {"thread_id": thread_id}})
                if not state:
                    continue
                cv = state.get("channel_values", {})
                msgs = cv.get("messages", [])

                # 找第一条用户消息作为列表预览。
                preview = ""
                for m in msgs:
                    if getattr(m, "type", "") == "human":
                        content = getattr(m, "content", "")
                        preview = content[:80] if isinstance(content, str) else str(content)[:80]
                        break

                # multiagent 线程会带 ACP 编排前缀，用它区分来源。
                thread_source = (
                    "multiagent"
                    if preview.startswith("你正在由一个 ACP 编排层调度运行")
                    else "tui"
                )
                results.append({
                    "thread_id": thread_id,
                    "preview": preview or "(empty)",
                    "message_count": len(msgs),
                    "source": thread_source,
                })
            except Exception:
                results.append({
                    "thread_id": thread_id,
                    "preview": "(error)",
                    "message_count": 0,
                    "source": "unknown",
                })

        if source is not None:
            results = [r for r in results if r["source"] == source]
        return results

    return _run_sqlite_read(
        db_path,
        operation="list_threads",
        fallback=[],
        callback=_load,
    )


def load_thread_messages(db_path: str, thread_id: str) -> list[dict[str, Any]]:
    """Load thread history from checkpoint state.

    Returns a normalized event list for TUI replay:
    - text message: {"role": "...", "content": "..."}
    - tool record: {"kind": "tool", "name": "...", "args": {...}, "output": "...", "tool_call_id": "..."}
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langgraph.checkpoint.sqlite import SqliteSaver

    def _load(db: sqlite3.Connection) -> list[dict[str, Any]]:
        saver = SqliteSaver(db)
        saver.setup()
        state = saver.get({"configurable": {"thread_id": thread_id}})
        if not state:
            return []
        cv = state.get("channel_values", {})
        msgs = cv.get("messages", [])

        results: list[dict[str, Any]] = []
        tool_index_by_call_id: dict[str, int] = {}
        for m in msgs:
            if isinstance(m, HumanMessage):
                content = m.content if isinstance(m.content, str) else str(m.content)
                results.append({"role": "user", "content": content})
            elif isinstance(m, AIMessage):
                # AI 回复优先取 text，兼容 token 流式聚合结果。
                content = getattr(m, "text", "") or ""
                if not content:
                    content = m.content if isinstance(m.content, str) else str(m.content)
                if not content.strip():
                    content = ""
                if content:
                    results.append({"role": "assistant", "content": content})

                # AIMessage 上会附带 tool_calls，恢复为工具记录。
                tool_calls = getattr(m, "tool_calls", None) or []
                for call in tool_calls:
                    call_id = str(call.get("id", "") or "")
                    name = str(call.get("name", "") or "")
                    args = call.get("args", {})
                    results.append(
                        {
                            "kind": "tool",
                            "name": name,
                            "args": args if isinstance(args, dict) else {},
                            "output": "",
                            "tool_call_id": call_id,
                        }
                    )
                    if call_id:
                        tool_index_by_call_id[call_id] = len(results) - 1
            elif isinstance(m, SystemMessage):
                content = m.content if isinstance(m.content, str) else str(m.content)
                results.append({"role": "system", "content": content})
            elif isinstance(m, ToolMessage):
                content = m.content if isinstance(m.content, str) else str(m.content)
                tool_call_id = str(getattr(m, "tool_call_id", "") or "")
                name = str(getattr(m, "name", "") or "")
                idx = tool_index_by_call_id.get(tool_call_id)
                if idx is not None:
                    results[idx]["output"] = content
                    if name and not results[idx].get("name"):
                        results[idx]["name"] = name
                else:
                    results.append(
                        {
                            "kind": "tool",
                            "name": name,
                            "args": {},
                            "output": content,
                            "tool_call_id": tool_call_id,
                        }
                    )
        return results

    return _run_sqlite_read(
        db_path,
        operation="load_thread_messages",
        fallback=[],
        callback=_load,
    )


def estimate_thread_tokens(db_path: str, thread_id: str) -> int:
    """估算指定线程当前状态占用的 token 数量。"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    from nocode_agent.compression.estimator import estimate_tokens

    def _load(db: sqlite3.Connection) -> int:
        saver = SqliteSaver(db)
        saver.setup()
        state = saver.get({"configurable": {"thread_id": thread_id}})
        if not state:
            return 0
        cv = state.get("channel_values", {})
        msgs = cv.get("messages", [])
        if not isinstance(msgs, list):
            return 0
        return estimate_tokens(msgs)

    return _run_sqlite_read(
        db_path,
        operation="estimate_thread_tokens",
        fallback=0,
        callback=_load,
    )


__all__ = [
    "CheckpointerManager",
    "estimate_thread_tokens",
    "list_threads",
    "load_thread_messages",
    "resolve_checkpoint_path",
]
