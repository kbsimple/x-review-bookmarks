"""Topics repository for topic taxonomy management.

ORG-02: User can create and manage a predefined topic taxonomy.
ORG-04: User can review and approve AI-suggested topic assignments.

Usage:
    from src.repositories import TopicsRepository
    from src.db import get_connection

    conn = get_connection()
    repo = TopicsRepository(conn)
    topic_id = repo.create_topic("Programming", "Software development")
    repo.assign_topic_to_post("post_123", topic_id)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


class TopicsRepository:
    """Repository for topics table and topic assignment operations."""

    def __init__(self, conn: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn

    # === Topic CRUD ===

    def create_topic(
        self,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> int:
        """Create a new topic.

        Args:
            name: Topic name (must be unique).
            description: Optional description.
            parent_id: Optional parent topic ID for hierarchy.

        Returns:
            Topic ID.

        Raises:
            sqlite3.IntegrityError: If name already exists.
        """
        cursor = self._conn.execute(
            "INSERT INTO topics (name, description, parent_id) VALUES (?, ?, ?)",
            (name, description, parent_id)
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_topic_by_id(self, topic_id: int) -> Optional[dict[str, Any]]:
        """Get topic by ID.

        Args:
            topic_id: Topic ID.

        Returns:
            Topic dict or None if not found.
        """
        row = self._conn.execute(
            "SELECT id, name, description, parent_id, created_at FROM topics WHERE id = ?",
            (topic_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_topic_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Get topic by name.

        Args:
            name: Topic name (exact match).

        Returns:
            Topic dict or None if not found.
        """
        row = self._conn.execute(
            "SELECT id, name, description, parent_id, created_at FROM topics WHERE name = ?",
            (name,)
        ).fetchone()
        return dict(row) if row else None

    def list_topics(self, include_hierarchy: bool = False) -> list[dict[str, Any]]:
        """List all topics.

        Args:
            include_hierarchy: If True, include child_count for each topic.

        Returns:
            List of topic dicts ordered by name.
        """
        if include_hierarchy:
            rows = self._conn.execute(
                """SELECT t.id, t.name, t.description, t.parent_id, t.created_at,
                          (SELECT COUNT(*) FROM topics WHERE parent_id = t.id) as child_count
                   FROM topics t
                   ORDER BY t.name"""
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, name, description, parent_id, created_at FROM topics ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def update_topic(
        self,
        topic_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> None:
        """Update topic fields.

        Args:
            topic_id: Topic ID.
            name: New name (optional).
            description: New description (optional).
            parent_id: New parent ID (optional, use None to clear).
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)

        if updates:
            params.append(topic_id)
            self._conn.execute(
                f"UPDATE topics SET {', '.join(updates)} WHERE id = ?",
                params
            )
            self._conn.commit()

    def delete_topic(self, topic_id: int) -> None:
        """Delete a topic.

        Cascade removes post_topics and pending_topic_assignments.
        Child topics have parent_id set to NULL.

        Args:
            topic_id: Topic ID to delete.
        """
        self._conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        self._conn.commit()

    # === Post-Topic Assignment ===

    def assign_topic_to_post(
        self,
        post_id: str,
        topic_id: int,
        confidence: Optional[float] = None,
        source: str = "user"
    ) -> None:
        """Assign a topic to a post.

        Args:
            post_id: X post ID.
            topic_id: Topic ID.
            confidence: Optional confidence score (0.0-1.0).
            source: 'user' or 'ai-approved'.
        """
        self._conn.execute(
            """INSERT OR REPLACE INTO post_topics
               (post_id, topic_id, confidence, source, assigned_at)
               VALUES (?, ?, ?, ?, ?)""",
            (post_id, topic_id, confidence, source, datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()

    def remove_topic_from_post(self, post_id: str, topic_id: int) -> None:
        """Remove a topic from a post.

        Args:
            post_id: X post ID.
            topic_id: Topic ID to remove.
        """
        self._conn.execute(
            "DELETE FROM post_topics WHERE post_id = ? AND topic_id = ?",
            (post_id, topic_id)
        )
        self._conn.commit()

    def get_post_topics(self, post_id: str) -> list[dict[str, Any]]:
        """Get all topics for a post.

        Args:
            post_id: X post ID.

        Returns:
            List of topic dicts with confidence and source.
        """
        rows = self._conn.execute(
            """SELECT t.id, t.name, t.description, pt.confidence, pt.source, pt.assigned_at
               FROM topics t
               JOIN post_topics pt ON t.id = pt.topic_id
               WHERE pt.post_id = ?
               ORDER BY t.name""",
            (post_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_posts_by_topic(self, topic_id: int) -> list[str]:
        """Get all post IDs assigned to a topic.

        Args:
            topic_id: Topic ID.

        Returns:
            List of post IDs.
        """
        rows = self._conn.execute(
            "SELECT post_id FROM post_topics WHERE topic_id = ?",
            (topic_id,)
        ).fetchall()
        return [row['post_id'] for row in rows]

    # === Pending Topic Assignments (ORG-04) ===

    def create_pending_assignment(
        self,
        post_id: str,
        topic_id: int,
        confidence: float
    ) -> int:
        """Create a pending AI-suggested topic assignment.

        ORG-04: User can review and approve AI-suggested topic assignments.

        Args:
            post_id: X post ID.
            topic_id: Suggested topic ID.
            confidence: AI confidence score (0.0-1.0).

        Returns:
            Pending assignment ID.
        """
        cursor = self._conn.execute(
            """INSERT INTO pending_topic_assignments (post_id, topic_id, confidence)
               VALUES (?, ?, ?)""",
            (post_id, topic_id, confidence)
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_pending_assignments(self, post_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Get pending topic assignments.

        Args:
            post_id: Optional filter by post ID.

        Returns:
            List of pending assignment dicts with topic info.
        """
        if post_id:
            rows = self._conn.execute(
                """SELECT pa.id, pa.post_id, pa.topic_id, pa.confidence, pa.suggested_at,
                          t.name as topic_name
                   FROM pending_topic_assignments pa
                   JOIN topics t ON pa.topic_id = t.id
                   WHERE pa.post_id = ?
                   ORDER BY pa.confidence DESC""",
                (post_id,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT pa.id, pa.post_id, pa.topic_id, pa.confidence, pa.suggested_at,
                          t.name as topic_name
                   FROM pending_topic_assignments pa
                   JOIN topics t ON pa.topic_id = t.id
                   ORDER BY pa.confidence DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def approve_pending_assignment(self, pending_id: int) -> None:
        """Approve a pending assignment.

        Moves the assignment from pending_topic_assignments to post_topics.

        Args:
            pending_id: Pending assignment ID.
        """
        # Get pending assignment
        row = self._conn.execute(
            "SELECT post_id, topic_id, confidence FROM pending_topic_assignments WHERE id = ?",
            (pending_id,)
        ).fetchone()

        if row:
            # Add to post_topics
            self._conn.execute(
                """INSERT OR REPLACE INTO post_topics
                   (post_id, topic_id, confidence, source, assigned_at)
                   VALUES (?, ?, ?, 'ai-approved', ?)""",
                (row['post_id'], row['topic_id'], row['confidence'],
                 datetime.now(timezone.utc).isoformat())
            )
            # Remove from pending
            self._conn.execute(
                "DELETE FROM pending_topic_assignments WHERE id = ?",
                (pending_id,)
            )
            self._conn.commit()

    def reject_pending_assignment(self, pending_id: int) -> None:
        """Reject a pending assignment.

        Simply deletes the pending assignment without creating a post_topic entry.

        Args:
            pending_id: Pending assignment ID.
        """
        self._conn.execute(
            "DELETE FROM pending_topic_assignments WHERE id = ?",
            (pending_id,)
        )
        self._conn.commit()

    def clear_pending_assignments(self, post_id: Optional[str] = None) -> int:
        """Clear pending assignments.

        Args:
            post_id: Optional filter by post. If None, clears all.

        Returns:
            Number of assignments cleared.
        """
        if post_id:
            cursor = self._conn.execute(
                "DELETE FROM pending_topic_assignments WHERE post_id = ?",
                (post_id,)
            )
        else:
            cursor = self._conn.execute("DELETE FROM pending_topic_assignments")
        self._conn.commit()
        return cursor.rowcount