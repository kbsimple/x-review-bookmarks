"""ReviewScheduler service for spaced repetition scheduling.

D-01: Uses FSRS-4.5 algorithm concepts with simplified user-controlled scheduling.
D-02: Seeds initial review state from publication date.
D-03: User intent intervals (fresh=3d, soon=14d, later=60d).
D-07: User chooses scheduling intent, not difficulty rating.
D-09: Postpone intervals without changing user_preference.

Usage:
    from src.services import ReviewScheduler

    scheduler = ReviewScheduler()
    initial_state = scheduler.create_initial_state(post_id, publication_date)
    updated_state = scheduler.schedule_review(state, 'fresh', review_time)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Literal

from fsrs import Card


class ReviewScheduler:
    """Simplified scheduler using FSRS Card state with user intervals.

    Uses FSRS's Card class for state tracking (stability, difficulty, retrievability)
    but applies simplified user-chosen intervals instead of FSRS's difficulty rating.

    User chooses scheduling intent:
    - 'fresh' = 3 days (keep content fresh)
    - 'soon' = 14 days (review again soon)
    - 'later' = 60 days (review much later)

    This simplification makes the system approachable while retaining FSRS's
    core state tracking for future algorithm enhancement.
    """

    # D-03: Default intervals for user choices
    INTERVALS: dict[Literal["fresh", "soon", "later"], timedelta] = {
        "fresh": timedelta(days=3),
        "soon": timedelta(weeks=2),  # 14 days
        "later": timedelta(days=60),
    }

    # D-09: Postpone intervals
    POSTPONE_INTERVALS: dict[str, timedelta] = {
        "1d": timedelta(days=1),
        "3d": timedelta(days=3),
        "1w": timedelta(weeks=1),
        "2w": timedelta(weeks=2),
        "1m": timedelta(days=30),
        "3m": timedelta(days=90),
    }

    # Maximum postpone days (1 year cap)
    MAX_POSTPONE_DAYS = 365

    def __init__(self):
        """Initialize scheduler with default FSRS parameters."""
        self.default_stability = 1.0
        self.default_difficulty = 0.3

    def create_initial_state(
        self,
        post_id: str,
        publication_date: datetime,
    ) -> dict:
        """D-02: Seed initial review state from publication date.

        Older posts naturally get scheduled immediately (age > 30 days).
        Newer posts get a small delay based on their age.

        Args:
            post_id: X post ID.
            publication_date: When the post was originally published.

        Returns:
            Dict with initial review state including FSRS Card JSON.
        """
        now = datetime.now(timezone.utc)
        age_days = (now - publication_date).days

        # Create FSRS Card with initial state
        card = Card()

        # D-02: Seed scheduled_for from publication date
        # Older posts (age > 30 days) are due immediately
        # Newer posts get a small delay based on age
        if age_days > 30:
            # Old posts: due immediately
            scheduled_for = now
        else:
            # New posts: seed with small delay based on age
            scheduled_for = now + timedelta(days=max(1, age_days // 10))

        return {
            "post_id": post_id,
            "scheduled_for": scheduled_for.isoformat(),
            "last_reviewed": None,
            "review_count": 0,
            "user_preference": None,
            "fsrs_data": json.dumps(card.to_dict()),
            "stability": self.default_stability,
            "difficulty": self.default_difficulty,
            "state": 0,  # New card state
        }

    def schedule_review(
        self,
        current_state: dict,
        user_choice: Literal["fresh", "soon", "later"],
        review_time: datetime,
    ) -> dict:
        """D-07: Apply user-chosen interval and update state.

        Args:
            current_state: Current review state dict.
            user_choice: One of 'fresh', 'soon', 'later'.
            review_time: When the review occurred (UTC).

        Returns:
            Updated state dict with new scheduled_for, user_preference, etc.

        Raises:
            ValueError: If user_choice is not valid.
        """
        # T-05-04: Validate user_choice
        if user_choice not in self.INTERVALS:
            valid_choices = ", ".join(self.INTERVALS.keys())
            raise ValueError(
                f"Invalid user_choice '{user_choice}'. Must be one of: {valid_choices}"
            )

        interval = self.INTERVALS[user_choice]

        # Parse existing FSRS state
        fsrs_data = current_state.get("fsrs_data", "{}")
        try:
            card = Card.from_dict(json.loads(fsrs_data))
        except (json.JSONDecodeError, TypeError):
            card = Card()

        # Calculate next due date
        scheduled_for = review_time + interval

        # Update state
        return {
            "post_id": current_state["post_id"],
            "scheduled_for": scheduled_for.isoformat(),
            "last_reviewed": review_time.isoformat(),
            "review_count": current_state.get("review_count", 0) + 1,
            "user_preference": user_choice,
            "fsrs_data": json.dumps(card.to_dict()),
            "stability": current_state.get("stability"),
            "difficulty": current_state.get("difficulty"),
            "state": current_state.get("state", 0),
            "step": current_state.get("step"),
        }

    def postpone_review(
        self,
        current_state: dict,
        days: int,
        postpone_time: datetime,
    ) -> dict:
        """D-09: Postpone review without changing user_preference.

        Postpone is a temporary delay - it does not affect the user's
        scheduling intent preference. The next review will still use
        the original user_preference.

        Args:
            current_state: Current review state dict.
            days: Number of days to postpone (capped at 365).
            postpone_time: When the postpone occurred (UTC).

        Returns:
            Updated state dict with new scheduled_for.

        Raises:
            ValueError: If days is not a positive integer.
        """
        # T-05-05: Validate days
        if days <= 0:
            raise ValueError("days must be a positive integer")
        if days > self.MAX_POSTPONE_DAYS:
            days = self.MAX_POSTPONE_DAYS

        scheduled_for = postpone_time + timedelta(days=days)

        # Return updated state, preserving user_preference
        return {
            **current_state,
            "scheduled_for": scheduled_for.isoformat(),
            # Do NOT change user_preference (D-09)
            # Do NOT increment review_count
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }