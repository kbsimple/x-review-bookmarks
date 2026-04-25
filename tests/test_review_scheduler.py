"""Tests for ReviewScheduler service.

Tests for FSRS Card state management and user-controlled scheduling intervals.

D-01: FSRS-4.5 concepts with simplified scheduling.
D-02: Seed initial state from publication date.
D-03: User intent intervals (fresh=3d, soon=14d, later=60d).
D-07: User chooses scheduling intent.
D-09: Postpone intervals without changing preference.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest
from fsrs import Card


def make_fsrs_data() -> str:
    """Create valid FSRS Card JSON for testing."""
    card = Card()
    return json.dumps(card.to_dict())


class TestReviewScheduler:
    """Tests for ReviewScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a ReviewScheduler instance for testing."""
        from src.services.review_scheduler import ReviewScheduler

        return ReviewScheduler()

    @pytest.fixture
    def old_publication_date(self):
        """Return a publication date older than 30 days."""
        return datetime(2024, 1, 1, tzinfo=timezone.utc)

    @pytest.fixture
    def new_publication_date(self):
        """Return a publication date within the last 30 days."""
        return datetime.now(timezone.utc) - timedelta(days=10)

    # Tests for INTERVALS constant (D-03)

    def test_intervals_constant_has_fresh(self, scheduler):
        """D-03: INTERVALS must include 'fresh' key with 3-day interval."""
        from datetime import timedelta

        assert "fresh" in scheduler.INTERVALS
        assert scheduler.INTERVALS["fresh"] == timedelta(days=3)

    def test_intervals_constant_has_soon(self, scheduler):
        """D-03: INTERVALS must include 'soon' key with 14-day interval."""
        from datetime import timedelta

        assert "soon" in scheduler.INTERVALS
        assert scheduler.INTERVALS["soon"] == timedelta(weeks=2)
        assert scheduler.INTERVALS["soon"] == timedelta(days=14)

    def test_intervals_constant_has_later(self, scheduler):
        """D-03: INTERVALS must include 'later' key with 60-day interval."""
        from datetime import timedelta

        assert "later" in scheduler.INTERVALS
        assert scheduler.INTERVALS["later"] == timedelta(days=60)

    # Tests for POSTPONE_INTERVALS constant (D-09)

    def test_postpone_intervals_has_fixed_options(self, scheduler):
        """D-09: POSTPONE_INTERVALS must have fixed interval options."""
        from datetime import timedelta

        assert "1d" in scheduler.POSTPONE_INTERVALS
        assert scheduler.POSTPONE_INTERVALS["1d"] == timedelta(days=1)

        assert "3d" in scheduler.POSTPONE_INTERVALS
        assert scheduler.POSTPONE_INTERVALS["3d"] == timedelta(days=3)

        assert "1w" in scheduler.POSTPONE_INTERVALS
        assert scheduler.POSTPONE_INTERVALS["1w"] == timedelta(weeks=1)

        assert "2w" in scheduler.POSTPONE_INTERVALS
        assert scheduler.POSTPONE_INTERVALS["2w"] == timedelta(weeks=2)

        assert "1m" in scheduler.POSTPONE_INTERVALS
        assert scheduler.POSTPONE_INTERVALS["1m"] == timedelta(days=30)

        assert "3m" in scheduler.POSTPONE_INTERVALS
        assert scheduler.POSTPONE_INTERVALS["3m"] == timedelta(days=90)

    # Tests for create_initial_state (D-02)

    def test_create_initial_state_creates_fsrs_card(self, scheduler):
        """D-02: create_initial_state must create FSRS Card."""
        post_id = "test_post_123"
        publication_date = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        state = scheduler.create_initial_state(post_id, publication_date)

        assert state["post_id"] == post_id
        assert "fsrs_data" in state
        assert state["fsrs_data"] is not None

    def test_create_initial_state_old_post_due_immediately(self, scheduler, old_publication_date):
        """D-02: Old posts (age > 30 days) should be due immediately."""
        post_id = "old_post_456"
        now = datetime.now(timezone.utc)

        state = scheduler.create_initial_state(post_id, old_publication_date)

        # scheduled_for should be approximately now (within 1 minute tolerance)
        scheduled_for = datetime.fromisoformat(state["scheduled_for"])
        assert scheduled_for <= now + timedelta(minutes=1)

    def test_create_initial_state_new_post_delayed(self, scheduler, new_publication_date):
        """D-02: New posts (age <= 30 days) should have delayed scheduled_for."""
        post_id = "new_post_789"

        state = scheduler.create_initial_state(post_id, new_publication_date)

        # scheduled_for should be in the future for new posts
        now = datetime.now(timezone.utc)
        scheduled_for = datetime.fromisoformat(state["scheduled_for"])

        # Should be scheduled in the future (age_days // 10 days from now)
        assert scheduled_for > now

    def test_create_initial_state_sets_review_count_zero(self, scheduler, new_publication_date):
        """D-02: Initial state must have review_count = 0."""
        state = scheduler.create_initial_state("test_post", new_publication_date)

        assert state["review_count"] == 0

    def test_create_initial_state_sets_user_preference_none(self, scheduler, new_publication_date):
        """D-02: Initial state must have user_preference = None."""
        state = scheduler.create_initial_state("test_post", new_publication_date)

        assert state["user_preference"] is None

    def test_create_initial_state_sets_last_reviewed_none(self, scheduler, new_publication_date):
        """D-02: Initial state must have last_reviewed = None."""
        state = scheduler.create_initial_state("test_post", new_publication_date)

        assert state["last_reviewed"] is None

    # Tests for schedule_review (D-03, D-07)

    def test_schedule_review_fresh_interval(self, scheduler):
        """D-03, D-07: schedule_review applies 'fresh' = 3-day interval."""
        current_state = {
            "post_id": "test_post",
            "review_count": 0,
            "user_preference": None,
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = scheduler.schedule_review(current_state, "fresh", review_time)

        assert updated["user_preference"] == "fresh"
        scheduled_for = datetime.fromisoformat(updated["scheduled_for"])
        expected = review_time + timedelta(days=3)
        assert scheduled_for == expected

    def test_schedule_review_soon_interval(self, scheduler):
        """D-03, D-07: schedule_review applies 'soon' = 14-day interval."""
        current_state = {
            "post_id": "test_post",
            "review_count": 1,
            "user_preference": "fresh",
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = scheduler.schedule_review(current_state, "soon", review_time)

        assert updated["user_preference"] == "soon"
        scheduled_for = datetime.fromisoformat(updated["scheduled_for"])
        expected = review_time + timedelta(days=14)
        assert scheduled_for == expected

    def test_schedule_review_later_interval(self, scheduler):
        """D-03, D-07: schedule_review applies 'later' = 60-day interval."""
        current_state = {
            "post_id": "test_post",
            "review_count": 2,
            "user_preference": "soon",
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = scheduler.schedule_review(current_state, "later", review_time)

        assert updated["user_preference"] == "later"
        scheduled_for = datetime.fromisoformat(updated["scheduled_for"])
        expected = review_time + timedelta(days=60)
        assert scheduled_for == expected

    def test_schedule_review_increments_review_count(self, scheduler):
        """D-07: schedule_review must increment review_count."""
        current_state = {
            "post_id": "test_post",
            "review_count": 0,
            "user_preference": None,
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime.now(timezone.utc)

        updated = scheduler.schedule_review(current_state, "fresh", review_time)

        assert updated["review_count"] == 1

    def test_schedule_review_sets_last_reviewed(self, scheduler):
        """D-07: schedule_review must set last_reviewed to review_time."""
        current_state = {
            "post_id": "test_post",
            "review_count": 0,
            "user_preference": None,
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime(2024, 6, 15, 9, 30, 0, tzinfo=timezone.utc)

        updated = scheduler.schedule_review(current_state, "fresh", review_time)

        last_reviewed = datetime.fromisoformat(updated["last_reviewed"])
        assert last_reviewed == review_time

    def test_schedule_review_updates_user_preference(self, scheduler):
        """D-07: schedule_review must update user_preference."""
        current_state = {
            "post_id": "test_post",
            "review_count": 0,
            "user_preference": None,
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime.now(timezone.utc)

        updated = scheduler.schedule_review(current_state, "soon", review_time)

        assert updated["user_preference"] == "soon"

    # Tests for postpone_review (D-09)

    def test_postpone_review_updates_scheduled_for(self, scheduler):
        """D-09: postpone_review must update scheduled_for."""
        current_state = {
            "post_id": "test_post",
            "scheduled_for": "2024-06-01T00:00:00+00:00",
            "user_preference": "fresh",
            "review_count": 1,
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = scheduler.postpone_review(current_state, days=7, postpone_time=postpone_time)

        scheduled_for = datetime.fromisoformat(updated["scheduled_for"])
        expected = postpone_time + timedelta(days=7)
        assert scheduled_for == expected

    def test_postpone_review_does_not_change_user_preference(self, scheduler):
        """D-09: postpone_review must NOT change user_preference."""
        current_state = {
            "post_id": "test_post",
            "scheduled_for": "2024-06-01T00:00:00+00:00",
            "user_preference": "fresh",
            "review_count": 1,
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = scheduler.postpone_review(current_state, days=3, postpone_time=postpone_time)

        assert updated["user_preference"] == "fresh"

    def test_postpone_review_does_not_increment_review_count(self, scheduler):
        """D-09: postpone_review must NOT increment review_count."""
        current_state = {
            "post_id": "test_post",
            "scheduled_for": "2024-06-01T00:00:00+00:00",
            "user_preference": "fresh",
            "review_count": 5,
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime.now(timezone.utc)

        updated = scheduler.postpone_review(current_state, days=1, postpone_time=postpone_time)

        assert updated["review_count"] == 5

    def test_postpone_review_custom_days(self, scheduler):
        """D-09: postpone_review supports custom --days interval."""
        current_state = {
            "post_id": "test_post",
            "scheduled_for": "2024-06-01T00:00:00+00:00",
            "user_preference": "soon",
            "review_count": 2,
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        updated = scheduler.postpone_review(current_state, days=45, postpone_time=postpone_time)

        scheduled_for = datetime.fromisoformat(updated["scheduled_for"])
        expected = postpone_time + timedelta(days=45)
        assert scheduled_for == expected

    # Tests for FSRS Card serialization

    def test_fsrs_card_serialization_round_trip(self, scheduler):
        """FSRS Card serialization must round-trip correctly."""
        import json
        from fsrs import Card

        # Create a Card
        card = Card()

        # Serialize to JSON via to_dict
        json_str = json.dumps(card.to_dict())

        # Deserialize back
        restored = Card.from_dict(json.loads(json_str))

        # Card should have default FSRS attributes
        assert hasattr(restored, "stability")
        assert hasattr(restored, "difficulty")

    def test_create_initial_state_includes_valid_fsrs_data(self, scheduler, new_publication_date):
        """D-01: create_initial_state must include valid FSRS Card JSON."""
        import json
        from fsrs import Card

        state = scheduler.create_initial_state("test_post", new_publication_date)

        # Should be able to deserialize fsrs_data
        card = Card.from_dict(json.loads(state["fsrs_data"]))
        # Card should have FSRS attributes
        assert hasattr(card, "stability")
        assert hasattr(card, "difficulty")

    def test_schedule_review_preserves_fsrs_data(self, scheduler):
        """D-07: schedule_review must preserve FSRS Card data."""
        import json
        from fsrs import Card

        current_state = {
            "post_id": "test_post",
            "review_count": 0,
            "user_preference": None,
            "fsrs_data": json.dumps(Card().to_dict()),
        }
        review_time = datetime.now(timezone.utc)

        updated = scheduler.schedule_review(current_state, "fresh", review_time)

        # FSRS data should still be present and valid
        assert "fsrs_data" in updated
        card = Card.from_dict(json.loads(updated["fsrs_data"]))
        assert hasattr(card, "stability")


class TestReviewSchedulerInputValidation:
    """Tests for input validation in ReviewScheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create a ReviewScheduler instance for testing."""
        from src.services.review_scheduler import ReviewScheduler

        return ReviewScheduler()

    def test_schedule_review_invalid_user_choice_raises_error(self, scheduler):
        """T-05-04: Invalid user_choice must raise error."""
        current_state = {
            "post_id": "test_post",
            "review_count": 0,
            "fsrs_data": make_fsrs_data(),
        }
        review_time = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="Invalid user_choice"):
            scheduler.schedule_review(current_state, "invalid_choice", review_time)

    def test_postpone_review_negative_days_raises_error(self, scheduler):
        """T-05-05: Negative days must raise error."""
        current_state = {
            "post_id": "test_post",
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="days must be a positive integer"):
            scheduler.postpone_review(current_state, days=-5, postpone_time=postpone_time)

    def test_postpone_review_zero_days_raises_error(self, scheduler):
        """T-05-05: Zero days must raise error."""
        current_state = {
            "post_id": "test_post",
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="days must be a positive integer"):
            scheduler.postpone_review(current_state, days=0, postpone_time=postpone_time)

    def test_postpone_review_days_capped_at_365(self, scheduler):
        """T-05-05: Days greater than 365 must be capped."""
        current_state = {
            "post_id": "test_post",
            "scheduled_for": "2024-06-01T00:00:00+00:00",
            "user_preference": "later",
            "review_count": 3,
            "fsrs_data": make_fsrs_data(),
        }
        postpone_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Request 500 days, should cap at 365
        updated = scheduler.postpone_review(current_state, days=500, postpone_time=postpone_time)

        scheduled_for = datetime.fromisoformat(updated["scheduled_for"])
        expected = postpone_time + timedelta(days=365)
        assert scheduled_for == expected