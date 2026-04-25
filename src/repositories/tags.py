"""Tags repository for tag management operations.

ORG-01: User can assign tags to bookmarked posts.

Usage:
    from src.repositories import TagsRepository
    from src.db import get_connection

    conn = get_connection()
    repo = TagsRepository(conn)
    tag_id = repo.get_or_create_tag("python")
    repo.assign_tag("post_123", tag_id)
"""

from __future__ import annotations

import sqlite3
from typing import Any


class TagsRepository:
    """Repository for tags table CRUD operations."""

    def __init__(self, conn: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn

    def get_or_create_tag(self, name: str) -> int:
        """Get tag ID, creating if needed. Returns tag ID.

        Normalizes name to lowercase and strips whitespace.

        Args:
            name: Tag name (will be normalized).

        Returns:
            Tag ID (int).
        """
        name = name.lower().strip()
        row = self._conn.execute(
            "SELECT id FROM tags WHERE name = ?", (name,)
        ).fetchone()

        if row:
            return row['id']

        cursor = self._conn.execute(
            "INSERT INTO tags (name) VALUES (?)", (name,)
        )
        self._conn.commit()
        return cursor.lastrowid

    def assign_tag(self, post_id: str, tag_id: int) -> None:
        """Assign a tag to a post (idempotent).

        Args:
            post_id: X post ID.
            tag_id: Tag ID from tags table.
        """
        self._conn.execute(
            "INSERT OR IGNORE INTO post_tags (post_id, tag_id) VALUES (?, ?)",
            (post_id, tag_id)
        )
        self._conn.commit()

    def remove_tag(self, post_id: str, tag_id: int) -> None:
        """Remove a tag from a post.

        Args:
            post_id: X post ID.
            tag_id: Tag ID to remove.
        """
        self._conn.execute(
            "DELETE FROM post_tags WHERE post_id = ? AND tag_id = ?",
            (post_id, tag_id)
        )
        self._conn.commit()

    def get_post_tags(self, post_id: str) -> list[dict[str, Any]]:
        """Get all tags for a post.

        Args:
            post_id: X post ID.

        Returns:
            List of dicts: [{"id": int, "name": str, "created_at": str}]
        """
        rows = self._conn.execute(
            """SELECT t.id, t.name, pt.created_at
               FROM tags t
               JOIN post_tags pt ON t.id = pt.tag_id
               WHERE pt.post_id = ?
               ORDER BY t.name""",
            (post_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_posts_by_tag(self, tag_id: int) -> list[str]:
        """Get all post IDs with a specific tag.

        Args:
            tag_id: Tag ID.

        Returns:
            List of post IDs (strings).
        """
        rows = self._conn.execute(
            "SELECT post_id FROM post_tags WHERE tag_id = ?",
            (tag_id,)
        ).fetchall()
        return [row['post_id'] for row in rows]

    def list_tags(self) -> list[dict[str, Any]]:
        """List all tags in alphabetical order.

        Returns:
            List of dicts: [{"id": int, "name": str, "created_at": str}]
        """
        rows = self._conn.execute(
            "SELECT id, name, created_at FROM tags ORDER BY name"
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_tag(self, tag_id: int) -> None:
        """Delete a tag (cascade removes post_tags entries).

        Args:
            tag_id: Tag ID to delete.
        """
        self._conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self._conn.commit()

    def get_tag_by_name(self, name: str) -> dict[str, Any] | None:
        """Get tag by name (normalized).

        Args:
            name: Tag name (will be normalized).

        Returns:
            Tag dict or None if not found.
        """
        name = name.lower().strip()
        row = self._conn.execute(
            "SELECT id, name, created_at FROM tags WHERE name = ?",
            (name,)
        ).fetchone()
        return dict(row) if row else None