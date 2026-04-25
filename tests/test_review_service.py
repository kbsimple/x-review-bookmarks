"""Tests for ReviewService orchestration layer.

Tests for the service that coordinates ReviewStateRepository, PostsRepository,
and ReviewScheduler for review operations.

D-02: Seed new posts from publication date.
SPAC-02: Get due posts for review.
SPAC-04: Filter by topic for themed reviews.
D-07: Process user's scheduling choice.
D-09: Postpone without changing preference.
D-12: Get review statistics.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json

import pytest
from fsrs import Card

from src.repositories.review_state import ReviewStateRepository
from src.repositories.posts import PostsRepository
from src.services.review_service import ReviewService


class TestReviewServiceSeedNewPosts:
    """Tests for seed_new_posts method."""

    @pytest.fixture
    def service(self, temp_db_v5):
        """Create a ReviewService instance for testing."""
        return ReviewService(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create a PostsRepository instance for testing."""
        return PostsRepository(temp_db_v5)

    def test_seed_new_posts_creates_review_state(self, service, posts_repo):
        """D-02: seed_new_posts creates review state for posts without state."""
        # Create a sample post
        post = {
            "x_post_id": "test_post_123",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post content",
            "author_id": "author_123",
            "author_username": "testuser",
        }
        posts_repo.insert_post(post)

        # Seed new posts
        seeded = service.seed_new_posts()

        # Should have seeded 1 post
        assert seeded == 1

    def test_seed_new_posts_sets_scheduled_from_publication(self, service, posts_repo):
        """D-02: seed_new_posts uses posts.created_at as scheduling baseline."""
        # Create posts with different ages
        old_post = {
            "x_post_id": "old_post",
            "created_at": "2024-01-01T00:00:00Z",  # > 30 days old
            "text": "Old post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        new_post = {
            "x_post_id": "new_post",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "text": "New post",
            "author_id": "author_2",
            "author_username": "user2",
        }
        posts_repo.insert_post(old_post)
        posts_repo.insert_post(new_post)

        # Seed new posts
        service.seed_new_posts()

        # Check review state for old post (should be due immediately)
        repo = ReviewStateRepository(posts_repo._conn)
        old_state = repo.get_state("old_post")
        assert old_state is not None
        # Old posts should have scheduled_for <= now
        scheduled_for = datetime.fromisoformat(old_state["scheduled_for"])
        assert scheduled_for <= datetime.now(timezone.utc) + timedelta(minutes=1)

    def test_seed_new_posts_skips_existing_state(self, service, posts_repo):
        """seed_new_posts does not create duplicate review states."""
        # Create a post
        post = {
            "x_post_id": "existing_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Existing post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        # Seed once
        first_seed = service.seed_new_posts()

        # Seed again - should not create duplicates
        second_seed = service.seed_new_posts()

        assert first_seed == 1
        assert second_seed == 0


class TestReviewServiceGetDuePosts:
    """Tests for get_due_posts method."""

    @pytest.fixture
    def service(self, temp_db_v5):
        """Create a ReviewService instance for testing."""
        return ReviewService(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create a PostsRepository instance for testing."""
        return PostsRepository(temp_db_v5)

    @pytest.fixture
    def review_repo(self, temp_db_v5):
        """Create a ReviewStateRepository instance for testing."""
        return ReviewStateRepository(temp_db_v5)

    def test_get_due_posts_returns_posts_scheduled_for_past(self, service, posts_repo, review_repo):
        """SPAC-02: get_due_posts returns posts where scheduled_for <= NOW."""
        # Create a post with review state scheduled for the past
        post = {
            "x_post_id": "due_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Due post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        # Create review state scheduled for yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()
        review_state = {
            "post_id": "due_post",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        }
        review_repo.create_state(review_state)

        # Get due posts
        due_posts = service.get_due_posts()

        # Should include the due post
        assert len(due_posts) >= 1
        due_post_ids = [p["post_id"] for p in due_posts]
        assert "due_post" in due_post_ids

    def test_get_due_posts_excludes_future_scheduled(self, service, posts_repo, review_repo):
        """SPAC-02: get_due_posts excludes posts with future scheduled_for."""
        # Create a post with review state scheduled for the future
        post = {
            "x_post_id": "future_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Future post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        # Create review state scheduled for tomorrow
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        card = Card()
        review_state = {
            "post_id": "future_post",
            "scheduled_for": tomorrow.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        }
        review_repo.create_state(review_state)

        # Get due posts
        due_posts = service.get_due_posts()

        # Should not include the future post
        due_post_ids = [p["post_id"] for p in due_posts]
        assert "future_post" not in due_post_ids


class TestReviewServiceGetDuePostsByTopic:
    """Tests for get_due_posts with topic filtering (SPAC-04)."""

    @pytest.fixture
    def service(self, temp_db_v5):
        """Create a ReviewService instance for testing."""
        return ReviewService(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create a PostsRepository instance for testing."""
        return PostsRepository(temp_db_v5)

    @pytest.fixture
    def review_repo(self, temp_db_v5):
        """Create a ReviewStateRepository instance for testing."""
        return ReviewStateRepository(temp_db_v5)

    def test_get_due_posts_filters_by_topic(self, service, posts_repo, review_repo, temp_db_v5):
        """SPAC-04: get_due_posts filters by topic_id when provided."""
        # Create a topic
        temp_db_v5.execute(
            "INSERT INTO topics (name, description) VALUES (?, ?)",
            ("Python", "Python programming"),
        )
        temp_db_v5.commit()
        topic_id = temp_db_v5.execute(
            "SELECT id FROM topics WHERE name = ?", ("Python",)
        ).fetchone()["id"]

        # Create posts
        post1 = {
            "x_post_id": "python_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Python post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        post2 = {
            "x_post_id": "other_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Other post",
            "author_id": "author_2",
            "author_username": "user2",
        }
        posts_repo.insert_post(post1)
        posts_repo.insert_post(post2)

        # Create review states (due)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()

        review_repo.create_state({
            "post_id": "python_post",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })
        review_repo.create_state({
            "post_id": "other_post",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        # Assign topic to python_post
        temp_db_v5.execute(
            "INSERT INTO post_topics (post_id, topic_id, source) VALUES (?, ?, ?)",
            ("python_post", topic_id, "user"),
        )
        temp_db_v5.commit()

        # Get due posts with topic filter
        due_posts = service.get_due_posts(topic_id=topic_id)

        # Should only return python_post
        assert len(due_posts) == 1
        assert due_posts[0]["post_id"] == "python_post"


class TestReviewServiceProcessReviewChoice:
    """Tests for process_review_choice method."""

    @pytest.fixture
    def service(self, temp_db_v5):
        """Create a ReviewService instance for testing."""
        return ReviewService(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create a PostsRepository instance for testing."""
        return PostsRepository(temp_db_v5)

    @pytest.fixture
    def review_repo(self, temp_db_v5):
        """Create a ReviewStateRepository instance for testing."""
        return ReviewStateRepository(temp_db_v5)

    def test_process_review_choice_updates_state(self, service, posts_repo, review_repo):
        """D-07: process_review_choice updates state and returns next scheduled date."""
        # Create a post with review state
        post = {
            "x_post_id": "test_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()
        review_repo.create_state({
            "post_id": "test_post",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        # Process review choice 'fresh'
        review_time = datetime.now(timezone.utc)
        next_date = service.process_review_choice("test_post", "fresh", review_time)

        # Verify next scheduled date
        expected = review_time + timedelta(days=3)
        assert next_date.date() == expected.date()

        # Verify state was updated
        state = review_repo.get_state("test_post")
        assert state["user_preference"] == "fresh"
        assert state["review_count"] == 1

    def test_process_review_choice_soon_interval(self, service, posts_repo, review_repo):
        """D-07: process_review_choice 'soon' uses 14-day interval."""
        post = {
            "x_post_id": "test_post_soon",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()
        review_repo.create_state({
            "post_id": "test_post_soon",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        review_time = datetime.now(timezone.utc)
        next_date = service.process_review_choice("test_post_soon", "soon", review_time)

        expected = review_time + timedelta(days=14)
        assert next_date.date() == expected.date()

    def test_process_review_choice_later_interval(self, service, posts_repo, review_repo):
        """D-07: process_review_choice 'later' uses 60-day interval."""
        post = {
            "x_post_id": "test_post_later",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()
        review_repo.create_state({
            "post_id": "test_post_later",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        review_time = datetime.now(timezone.utc)
        next_date = service.process_review_choice("test_post_later", "later", review_time)

        expected = review_time + timedelta(days=60)
        assert next_date.date() == expected.date()


class TestReviewServiceProcessPostpone:
    """Tests for process_postpone method."""

    @pytest.fixture
    def service(self, temp_db_v5):
        """Create a ReviewService instance for testing."""
        return ReviewService(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create a PostsRepository instance for testing."""
        return PostsRepository(temp_db_v5)

    @pytest.fixture
    def review_repo(self, temp_db_v5):
        """Create a ReviewStateRepository instance for testing."""
        return ReviewStateRepository(temp_db_v5)

    def test_process_postpone_updates_scheduled_for(self, service, posts_repo, review_repo):
        """D-09: process_postpone updates scheduled_for."""
        post = {
            "x_post_id": "postpone_test",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()
        review_repo.create_state({
            "post_id": "postpone_test",
            "scheduled_for": yesterday.isoformat(),
            "user_preference": "fresh",
            "review_count": 2,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        postpone_time = datetime.now(timezone.utc)
        next_date = service.process_postpone("postpone_test", days=7, postpone_time=postpone_time)

        expected = postpone_time + timedelta(days=7)
        assert next_date.date() == expected.date()

    def test_process_postpone_preserves_user_preference(self, service, posts_repo, review_repo):
        """D-09: process_postpone does NOT change user_preference."""
        post = {
            "x_post_id": "postpone_pref",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post",
            "author_id": "author_1",
            "author_username": "user1",
        }
        posts_repo.insert_post(post)

        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        card = Card()
        review_repo.create_state({
            "post_id": "postpone_pref",
            "scheduled_for": yesterday.isoformat(),
            "user_preference": "soon",
            "review_count": 3,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        service.process_postpone("postpone_pref", days=14)

        state = review_repo.get_state("postpone_pref")
        assert state["user_preference"] == "soon"  # Unchanged


class TestReviewServiceGetReviewStats:
    """Tests for get_review_stats method."""

    @pytest.fixture
    def service(self, temp_db_v5):
        """Create a ReviewService instance for testing."""
        return ReviewService(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create a PostsRepository instance for testing."""
        return PostsRepository(temp_db_v5)

    @pytest.fixture
    def review_repo(self, temp_db_v5):
        """Create a ReviewStateRepository instance for testing."""
        return ReviewStateRepository(temp_db_v5)

    def test_get_review_stats_returns_counts(self, service, posts_repo, review_repo):
        """D-12: get_review_stats returns total_posts, due_count, reviewed_count."""
        # Create posts
        for i in range(3):
            post = {
                "x_post_id": f"post_{i}",
                "created_at": "2024-01-01T00:00:00Z",
                "text": f"Post {i}",
                "author_id": "author_1",
                "author_username": "user1",
            }
            posts_repo.insert_post(post)

        # Create review states
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        card = Card()

        # Post 0: due, not reviewed
        review_repo.create_state({
            "post_id": "post_0",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })
        # Post 1: due, reviewed
        review_repo.create_state({
            "post_id": "post_1",
            "scheduled_for": yesterday.isoformat(),
            "review_count": 2,
            "fsrs_data": json.dumps(card.to_dict()),
        })
        # Post 2: not due, not reviewed
        review_repo.create_state({
            "post_id": "post_2",
            "scheduled_for": tomorrow.isoformat(),
            "review_count": 0,
            "fsrs_data": json.dumps(card.to_dict()),
        })

        stats = service.get_review_stats()

        assert stats["total_posts"] == 3
        assert stats["due_count"] == 2  # post_0 and post_1
        assert stats["reviewed_count"] == 1  # post_1 (review_count > 0)