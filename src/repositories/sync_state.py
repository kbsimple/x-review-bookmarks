"""Sync state repository for incremental sync tracking.

D-02: Incremental sync via bookmark ID comparison.
STOR-03: Incremental sync (only fetch new bookmarks).

Usage:
    from src.repositories import SyncStateRepository
    from src.db import get_connection

    conn = get_connection()
    repo = SyncStateRepository(conn)
    state = repo.get_state()
    repo.update_state(last_bookmark_id="12345")
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SyncState:
    """Current sync state for incremental sync.

    Attributes:
        last_sync_bookmark_id: Highest x_post_id seen in last sync.
        last_sync_at: Timestamp of last successful sync.
        pagination_token: Token for resuming interrupted sync.
        total_bookmarks: Total bookmarks count (for 800 limit tracking).
    """
    last_sync_bookmark_id: Optional[str] = None
    last_sync_at: Optional[float] = None
    pagination_token: Optional[str] = None
    total_bookmarks: int = 0


class SyncStateRepository:
    """Repository for sync_state table operations.

    Manages the single-row sync_state table for:
    - Tracking last synced bookmark ID (incremental sync)
    - Storing pagination token (resume after interruption)
    - Counting total bookmarks (800 limit warning)
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn
        self._ensure_row_exists()

    def _ensure_row_exists(self) -> None:
        """Ensure the single sync_state row exists."""
        self._conn.execute(
            "INSERT OR IGNORE INTO sync_state (id) VALUES (1)"
        )
        self._conn.commit()

    def get_state(self) -> SyncState:
        """Get current sync state.

        Returns:
            SyncState with current values, or defaults if not set.
        """
        row = self._conn.execute(
            "SELECT * FROM sync_state WHERE id = 1"
        ).fetchone()

        if row is None:
            return SyncState()

        return SyncState(
            last_sync_bookmark_id=row['last_sync_bookmark_id'],
            last_sync_at=row['last_sync_at'],
            pagination_token=row['pagination_token'],
            total_bookmarks=row['total_bookmarks'] or 0,
        )

    def update_state(
        self,
        last_sync_bookmark_id: Optional[str] = None,
        pagination_token: Optional[str] = None,
        reset_pagination: bool = False,
    ) -> None:
        """Update sync state after fetching bookmarks.

        Args:
            last_sync_bookmark_id: Highest bookmark ID seen.
            pagination_token: Token for resuming (or None if sync complete).
            reset_pagination: If True, clear pagination_token.
        """
        now = time.time()

        if reset_pagination:
            pagination_token = None

        self._conn.execute(
            """
            UPDATE sync_state SET
                last_sync_bookmark_id = COALESCE(?, last_sync_bookmark_id),
                last_sync_at = ?,
                pagination_token = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (last_sync_bookmark_id, now, pagination_token)
        )
        self._conn.commit()

    def increment_count(self, count: int) -> None:
        """Add to total bookmarks count.

        Args:
            count: Number of new bookmarks to add.
        """
        self._conn.execute(
            """
            UPDATE sync_state SET
                total_bookmarks = total_bookmarks + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (count,)
        )
        self._conn.commit()

    def set_total_count(self, total: int) -> None:
        """Set total bookmarks count directly.

        Used after full sync to set accurate count.

        Args:
            total: Total number of bookmarks.
        """
        self._conn.execute(
            """
            UPDATE sync_state SET
                total_bookmarks = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (total,)
        )
        self._conn.commit()