"""Review state repository for spaced repetition scheduling.

SPAC-01: Review state table for spaced repetition scheduling.
SPAC-02: get_due_posts query returns posts due for review.
SPAC-04: Themed reviews filter by topic via post_topics join.

Usage:
    from src.repositories import ReviewStateRepository
    from src.db import get_connection

    conn = get_connection()
    repo = ReviewStateRepository(conn)
    due_posts = repo.get_due_posts()
"""

from __future__ import annotations

import sqlite3
from typing import Any, Optional


class ReviewStateRepository:
    """Repository for post_review_state table CRUD operations.

    Handles all database operations for the post_review_state table:
    - Create/read/update/delete review state for posts
    - Query posts due for review
    - Get review statistics
    """

    # Allowed columns for update operations (SQL injection defense)
    UPDATEABLE_COLUMNS = frozenset({
        'scheduled_for', 'last_reviewed', 'review_count',
        'user_preference', 'stability', 'difficulty', 'state', 'step', 'fsrs_data'
    })

    def __init__(self, conn: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn

    def create_state(self, state: dict[str, Any]) -> None:
        """Insert new review state for a post.

        SPAC-01: Create review state with FSRS parameters.

        Args:
            state: Dict with review state fields.
                  Required: post_id, scheduled_for
                  Optional: last_reviewed, review_count, user_preference,
                           stability, difficulty, state, step, fsrs_data
        """
        self._conn.execute(
            """INSERT INTO post_review_state (
                post_id, scheduled_for, last_reviewed, review_count,
                user_preference, stability, difficulty, state, step, fsrs_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state['post_id'],
                state['scheduled_for'],
                state.get('last_reviewed'),
                state.get('review_count', 0),
                state.get('user_preference'),
                state.get('stability'),
                state.get('difficulty'),
                state.get('state', 0),
                state.get('step'),
                state.get('fsrs_data'),
            )
        )
        self._conn.commit()

    def get_state(self, post_id: str) -> Optional[dict[str, Any]]:
        """Get review state for a post.

        Args:
            post_id: X post ID.

        Returns:
            Dict with review state, or None if not found.
        """
        row = self._conn.execute(
            """SELECT post_id, scheduled_for, last_reviewed, review_count,
                      user_preference, stability, difficulty, state, step,
                      fsrs_data, created_at, updated_at
               FROM post_review_state WHERE post_id = ?""",
            (post_id,)
        ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def update_state(self, state: dict[str, Any]) -> None:
        """Update review state after user choice.

        Updates the scheduled_for date and increments review_count.
        Also updates FSRS parameters if provided.

        Args:
            state: Dict with fields to update.
                  Required: post_id
                  Optional: scheduled_for, last_reviewed, review_count,
                           user_preference, stability, difficulty, state, step, fsrs_data

        Raises:
            ValueError: If any field name is not in the allowlist.
            KeyError: If post_id is missing from state dict.
        """
        if 'post_id' not in state:
            raise KeyError("post_id is required for update_state")

        # Build updates from state dict, validating against allowlist
        updates = []
        params = []

        for field in self.UPDATEABLE_COLUMNS:
            if field in state:
                # Column name is validated against allowlist (SQL injection defense)
                updates.append(f"{field} = ?")
                params.append(state[field])

        if updates:
            # Always update updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(state['post_id'])

            self._conn.execute(
                f"""UPDATE post_review_state
                    SET {', '.join(updates)}
                    WHERE post_id = ?""",
                params
            )
            self._conn.commit()

    def get_due_posts(
        self,
        topic_id: Optional[int] = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get posts due for review.

        SPAC-02: Returns posts where scheduled_for <= NOW.
        SPAC-04: Filters by topic if topic_id provided.

        Args:
            topic_id: Optional topic ID to filter by (themed reviews).
            limit: Maximum posts to return.

        Returns:
            List of post dicts with review state, ordered by scheduled_for ASC.
        """
        if topic_id is not None:
            # Themed review: join with post_topics
            rows = self._conn.execute(
                """SELECT prs.post_id, prs.scheduled_for, prs.last_reviewed,
                          prs.review_count, prs.user_preference, prs.state
                   FROM post_review_state prs
                   JOIN post_topics pt ON prs.post_id = pt.post_id
                   WHERE pt.topic_id = ?
                     AND prs.scheduled_for <= datetime('now')
                   ORDER BY prs.scheduled_for ASC
                   LIMIT ?""",
                (topic_id, limit)
            ).fetchall()
        else:
            # All due posts
            rows = self._conn.execute(
                """SELECT post_id, scheduled_for, last_reviewed,
                          review_count, user_preference, state
                   FROM post_review_state
                   WHERE scheduled_for <= datetime('now')
                   ORDER BY scheduled_for ASC
                   LIMIT ?""",
                (limit,)
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_stats(self) -> dict[str, int]:
        """Get review statistics.

        D-12: Returns total_posts, due_count, reviewed_count.

        Returns:
            Dict with:
            - total_posts: Total posts with review state
            - due_count: Posts scheduled for review (scheduled_for <= NOW)
            - reviewed_count: Posts reviewed at least once (review_count > 0)
        """
        # Total posts with review state
        total_row = self._conn.execute(
            "SELECT COUNT(*) as count FROM post_review_state"
        ).fetchone()
        total_posts = total_row['count'] if total_row else 0

        # Due posts (scheduled_for <= NOW)
        due_row = self._conn.execute(
            """SELECT COUNT(*) as count FROM post_review_state
               WHERE scheduled_for <= datetime('now')"""
        ).fetchone()
        due_count = due_row['count'] if due_row else 0

        # Reviewed posts (review_count > 0)
        reviewed_row = self._conn.execute(
            """SELECT COUNT(*) as count FROM post_review_state
               WHERE review_count > 0"""
        ).fetchone()
        reviewed_count = reviewed_row['count'] if reviewed_row else 0

        return {
            "total_posts": total_posts,
            "due_count": due_count,
            "reviewed_count": reviewed_count,
        }

    def get_all(self) -> list[dict[str, Any]]:
        """Get all review states for static export.

        EXPORT-01: Returns all review states for review_state.json generation.
        Excludes internal FSRS plumbing fields (user_preference, step, fsrs_data).

        Returns:
            List of dicts with keys: post_id, scheduled_for, last_reviewed,
            review_count, stability, difficulty, state.
            Ordered by post_id for deterministic output.
        """
        rows = self._conn.execute(
            """SELECT post_id, scheduled_for, last_reviewed, review_count,
                      stability, difficulty, state
               FROM post_review_state
               ORDER BY post_id"""
        ).fetchall()
        return [dict(row) for row in rows]

    def reset_state(self, post_id: str) -> None:
        """Delete review state for a post.

        D-13: Reset state for a post (e.g., when user wants to start over).

        Args:
            post_id: X post ID to reset.
        """
        self._conn.execute(
            "DELETE FROM post_review_state WHERE post_id = ?",
            (post_id,)
        )
        self._conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert a database row to dict.

        Args:
            row: SQLite Row object.

        Returns:
            Dict with review state fields.
        """
        return dict(row)