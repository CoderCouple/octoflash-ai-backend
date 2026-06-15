"""Streaming log sink — buffers lines from the Manim subprocess and
flushes them into `execution_log` every ~500 ms, scoped to a single
`scene_render` row.

Used by:
  * manim_render_service when an active SceneRender is in scope.
    Spawns reader threads for stdout/stderr of the manim subprocess
    and forwards each line to `LogSink.write()`. The sink owns a
    dedicated sync psycopg connection so the IO doesn't block the
    asyncio event loop in the calling activity.
  * generate_clip_activity at the start of every internal attempt.
    Creates one sink per attempt, passes it down, and closes it at
    attempt end so the final flush goes out.

Design notes:
  * One psycopg connection per LogSink (cheap on Supabase pooler).
  * Writes use a thread-safe deque + lock — no contention since the
    only producers are the two subprocess reader threads.
  * Multi-row INSERT via executemany. Supabase pooler accepts up to
    ~65k parameters per call; flush_max=200 keeps us well under.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


_FLUSH_INTERVAL_S = 0.5
_FLUSH_MAX_LINES = 200
_MAX_LINE_CHARS = 2048  # matches execution_log.message column length


class LogSink:
    """Buffers `(level, line, ts)` tuples + flushes them to
    `execution_log` every `_FLUSH_INTERVAL_S` seconds (or sooner when
    `_FLUSH_MAX_LINES` is reached).

    Thread-safe. The flusher runs on its own daemon thread; the reader
    threads from the Manim subprocess call `.write()` non-blocking.
    On `.close()` the flusher drains the buffer once more before the
    psycopg connection is returned.
    """

    def __init__(self, scene_render_id: str):
        from app.settings import settings
        import psycopg

        self.scene_render_id = scene_render_id
        self._buffer: deque[tuple[str, str, datetime]] = deque()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        # Dedicated sync connection. autocommit=True so each INSERT
        # lands without bookkeeping; the worker has its own pool for
        # real DB writes.
        self._conn = psycopg.connect(
            settings.sync_database_url.replace(
                "postgresql+psycopg://", "postgresql://"
            ),
            autocommit=True,
            connect_timeout=10,
        )
        self._flusher = threading.Thread(
            target=self._flush_loop, name=f"LogSink[{scene_render_id[:12]}]",
            daemon=True,
        )
        self._flusher.start()

    # ── producer side (called from subprocess reader threads) ────────

    def write(self, level: str, line: str) -> None:
        """Buffer one line. Truncates oversize messages so a runaway
        traceback doesn't blow the column."""
        if not line:
            return
        if len(line) > _MAX_LINE_CHARS:
            line = line[: _MAX_LINE_CHARS - 3] + "..."
        with self._lock:
            self._buffer.append((level, line, datetime.now(timezone.utc)))

    # ── consumer side (background thread) ────────────────────────────

    def _flush_loop(self) -> None:
        while not self._stop.is_set():
            self._flush_once()
            # `wait()` with a timeout returns False if not set, True if
            # set — letting us collapse a tight sleep + check.
            self._stop.wait(_FLUSH_INTERVAL_S)
        # Final drain on close.
        self._flush_once()

    def _flush_once(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch = list(self._buffer)
            self._buffer.clear()
        rows = [
            (
                f"execlog_{uuid.uuid4()}",
                self.scene_render_id,
                level,
                line,
                ts,
            )
            for level, line, ts in batch[: _FLUSH_MAX_LINES]
        ]
        try:
            cur = self._conn.cursor()
            cur.executemany(
                """
                INSERT INTO execution_log
                    (id, scene_render_id, log_level, message, timestamp, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, now(), now())
                """,
                rows,
            )
            # Print a single-line confirmation so the worker log shows
            # the streaming is actually working — saves a debugging
            # round-trip the next time the FE shows empty.
            logger.info(
                "LogSink flushed sr=%s rows=%d sample=%r",
                self.scene_render_id, len(rows), rows[0][3][:80] if rows else "",
            )
        except Exception as exc:  # noqa: BLE001
            # Don't propagate — logging shouldn't crash the render.
            # But make the failure loud — when the FE shows zero log
            # lines we want a single grep-able log line to know whether
            # the flush ran or was never reached.
            logger.error(
                "LogSink FLUSH FAILED sr=%s rows=%d err=%s: %s",
                self.scene_render_id, len(rows), type(exc).__name__, str(exc)[:200],
            )
            # Try to reopen the connection on next flush — silent
            # failures here are the worst kind. The next flush will
            # retry the conn.
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                import psycopg
                from app.settings import settings
                self._conn = psycopg.connect(
                    settings.sync_database_url.replace(
                        "postgresql+psycopg://", "postgresql://"
                    ),
                    autocommit=True,
                    connect_timeout=10,
                )
            except Exception:  # noqa: BLE001
                # If reconnect also fails, just give up gracefully.
                logger.exception("LogSink reconnect failed sr=%s", self.scene_render_id)

    # ── lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Stop the flusher, drain remaining buffer, close the
        connection. Safe to call more than once."""
        if self._stop.is_set():
            return
        self._stop.set()
        self._flusher.join(timeout=3)
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> "LogSink":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
