"""ReviewService orchestration layer for review operations.

D-02: Seeds initial review state from publication date.
SPAC-02: Gets due posts for review.
SPAC-04: Filters by topic for themed reviews.
D-07: Processes user's scheduling choice.
D-09: Postpones without changing preference.
D-12: Gets review statistics.

Usage:
    from src.services import ReviewService
    from src.db import get_connection

    conn = get_connection()
    service = ReviewService(conn)
    service.seed_new_posts()
    due_posts = service.get_due_posts()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from sqlite3 import Connection

from ..repositories.review_state import ReviewStateRepository
from ..repositories.posts import PostsRepository
from .review_scheduler import ReviewScheduler


class ReviewService:
    """Orchestrates review operations using repository and scheduler.

    Coordinates between:
    - ReviewStateRepository: CRUD for review state
    - PostsRepository: Post data
    - ReviewScheduler: Scheduling logic

    This service is the primary interface for CLI commands like:
    - xbm review: Interactive review sessions
    - xbm due: List due posts
    - xbm stats: Show statistics
    """

    def __init__(self, conn: Connection):
        """Initialize service with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn
        self._repo = ReviewStateRepository(conn)
        self._posts_repo = PostsRepository(conn)
        self._scheduler = ReviewScheduler()

    def seed_new_posts(self) -> int:
        """Create initial review state for posts without state.

        D-02: Seeds from posts.created_at (publication date).

        Returns:
            Number of posts seeded.
        """
        # Find posts without review state
        rows = self._conn.execute(
            """SELECT x_post_id, created_at FROM posts
               WHERE x_post_id NOT IN (SELECT post_id FROM post_review_state)"""
        ).fetchall()

        seeded = 0
        for row in rows:
            post_id = row["x_post_id"]
            # Parse publication date
            created_at_str = row["created_at"]
            if created_at_str.endswith("Z"):
                created_at_str = created_at_str[:-1] + "+00:00"
            publication_date = datetime.fromisoformat(created_at_str)

            # Create initial state
            state = self._scheduler.create_initial_state(post_id, publication_date)

            # Insert into review_state table
            self._repo.create_state({
                "post_id": state["post_id"],
                "scheduled_for": state["scheduled_for"],
                "last_reviewed": state.get("last_reviewed"),
                "review_count": state["review_count"],
                "user_preference": state.get("user_preference"),
                "stability": state.get("stability"),
                "difficulty": state.get("difficulty"),
                "state": state.get("state"),
                "step": state.get("step"),
                "fsrs_data": state.get("fsrs_data"),
            })
            seeded += 1

        return seeded

    def get_due_posts(
        self,
        topic_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get posts due for review.

        SPAC-02: Returns posts where scheduled_for <= NOW.
        SPAC-04: Filters by topic when topic_id provided.

        Args:
            topic_id: Optional topic ID for themed reviews.
            limit: Maximum posts to return.

        Returns:
            List of post dicts with review state, ordered by scheduled_for ASC.
        """
        # Get review state for due posts
        due_states = self._repo.get_due_posts(topic_id=topic_id, limit=limit)

        # Enrich with post data
        result = []
        for state in due_states:
            post = self._posts_repo.get_by_id(state["post_id"])
            if post:
                # Merge post data with review state
                merged = {**post, **state}
                result.append(merged)

        return result

    def process_review_choice(
        self,
        post_id: str,
        user_choice: Literal["fresh", "soon", "later"],
        review_time: Optional[datetime] = None,
    ) -> datetime:
        """Process user's scheduling choice.

        D-07: Applies user-chosen interval.

        Args:
            post_id: X post ID.
            user_choice: One of 'fresh', 'soon', 'later'.
            review_time: When the review occurred (defaults to now).

        Returns:
            Next scheduled date.

        Raises:
            ValueError: If post has no review state.
        """
        if review_time is None:
            review_time = datetime.now(timezone.utc)

        # Get current state
        current_state = self._repo.get_state(post_id)
        if current_state is None:
            raise ValueError(f"No review state found for post {post_id}")

        # Apply scheduling
        updated_state = self._scheduler.schedule_review(
            current_state, user_choice, review_time
        )

        # Persist changes
        self._repo.update_state(updated_state)

        # Return next scheduled date
        return datetime.fromisoformat(updated_state["scheduled_for"])

    def process_postpone(
        self,
        post_id: str,
        days: int,
        postpone_time: Optional[datetime] = None,
    ) -> datetime:
        """Postpone review without changing preference.

        D-09: Custom delay via days parameter.

        Args:
            post_id: X post ID.
            days: Number of days to postpone (capped at 365).
            postpone_time: When the postpone occurred (defaults to now).

        Returns:
            Next scheduled date.

        Raises:
            ValueError: If post has no review state.
        """
        if postpone_time is None:
            postpone_time = datetime.now(timezone.utc)

        # Get current state
        current_state = self._repo.get_state(post_id)
        if current_state is None:
            raise ValueError(f"No review state found for post {post_id}")

        # Apply postpone
        updated_state = self._scheduler.postpone_review(
            current_state, days, postpone_time
        )

        # Persist changes
        self._repo.update_state(updated_state)

        # Return next scheduled date
        return datetime.fromisoformat(updated_state["scheduled_for"])

    def get_review_stats(self) -> dict:
        """Get review statistics.

        D-12: Returns total_posts, due_count, reviewed_count.

        Returns:
            Dict with statistics.
        """
        return self._repo.get_stats()

    def reset_review_state(self, post_id: str) -> None:
        """Reset review state for a specific post.

        D-13: Clears existing state and allows re-seeding from publication date.

        Args:
            post_id: X post ID to reset.
        """
        self._repo.reset_state(post_id)