"""Tests for ReviewStateRepository.

Tests for:
- CRUD operations on post_review_state table
- get_due_posts query (SPAC-02)
- Themed reviews filtering by topic (SPAC-04)
- Statistics query (D-12)
"""

import pytest
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestReviewStateRepository:
    """Tests for ReviewStateRepository CRUD operations."""

    @pytest.fixture
    def temp_db_v5(self):
        """Create a temporary database with v5 schema."""
        import tempfile
        from src.db.schema import SCHEMA_V1, SCHEMA_V2
        from src.db.migrations import run_migrations

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Apply PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")

        # Apply v1 and v2 schemas
        conn.executescript(SCHEMA_V1)
        conn.executescript(SCHEMA_V2)
        conn.commit()

        # Run all migrations
        run_migrations(conn)

        yield conn

        conn.close()
        db_path.unlink(missing_ok=True)

    @pytest.fixture
    def repo(self, temp_db_v5):
        """Create ReviewStateRepository instance."""
        from src.repositories.review_state import ReviewStateRepository
        return ReviewStateRepository(temp_db_v5)

    @pytest.fixture
    def posts_repo(self, temp_db_v5):
        """Create PostsRepository instance for test setup."""
        from src.repositories.posts import PostsRepository
        return PostsRepository(temp_db_v5)

    @pytest.fixture
    def topics_repo(self, temp_db_v5):
        """Create TopicsRepository instance for themed review tests."""
        from src.repositories.topics import TopicsRepository
        return TopicsRepository(temp_db_v5)

    def test_create_state_inserts_new_review_state(self, temp_db_v5, repo, posts_repo):
        """Test 1: create_state inserts new review state for a post."""
        # Insert a post first
        posts_repo.insert_post({
            "x_post_id": "test_post_1",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post content",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create review state
        state = {
            "post_id": "test_post_1",
            "scheduled_for": "2024-01-15T00:00:00Z",
            "review_count": 0,
        }
        repo.create_state(state)

        # Verify state was inserted
        row = temp_db_v5.execute(
            "SELECT * FROM post_review_state WHERE post_id = ?",
            ("test_post_1",)
        ).fetchone()

        assert row is not None
        assert row["post_id"] == "test_post_1"
        assert row["scheduled_for"] == "2024-01-15T00:00:00Z"
        assert row["review_count"] == 0

    def test_get_state_returns_review_state_for_existing_post(self, temp_db_v5, repo, posts_repo):
        """Test 2: get_state returns review state for existing post."""
        # Insert a post
        posts_repo.insert_post({
            "x_post_id": "test_post_2",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post content",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create review state
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for, review_count, state)
            VALUES (?, ?, ?, ?)
        """, ("test_post_2", "2024-01-15T00:00:00Z", 3, 2))
        temp_db_v5.commit()

        # Get state
        result = repo.get_state("test_post_2")

        assert result is not None
        assert result["post_id"] == "test_post_2"
        assert result["scheduled_for"] == "2024-01-15T00:00:00Z"
        assert result["review_count"] == 3
        assert result["state"] == 2

    def test_get_state_returns_none_for_nonexistent_post(self, repo):
        """Test 3: get_state returns None for non-existent post."""
        result = repo.get_state("nonexistent_post")

        assert result is None

    def test_update_state_updates_scheduled_for_and_review_count(self, temp_db_v5, repo, posts_repo):
        """Test 4: update_state updates scheduled_for and review_count."""
        # Insert a post
        posts_repo.insert_post({
            "x_post_id": "test_post_4",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test post content",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create initial review state
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for, review_count, state)
            VALUES (?, ?, ?, ?)
        """, ("test_post_4", "2024-01-15T00:00:00Z", 0, 0))
        temp_db_v5.commit()

        # Update state
        repo.update_state({
            "post_id": "test_post_4",
            "scheduled_for": "2024-02-01T00:00:00Z",
            "review_count": 1,
            "state": 2,
            "stability": 5.5,
            "difficulty": 4.2,
        })

        # Verify update
        row = temp_db_v5.execute(
            "SELECT * FROM post_review_state WHERE post_id = ?",
            ("test_post_4",)
        ).fetchone()

        assert row["scheduled_for"] == "2024-02-01T00:00:00Z"
        assert row["review_count"] == 1
        assert row["state"] == 2
        assert row["stability"] == 5.5
        assert row["difficulty"] == 4.2

    def test_get_due_posts_returns_posts_where_scheduled_for_le_now(self, temp_db_v5, repo, posts_repo):
        """Test 5: get_due_posts returns posts where scheduled_for <= NOW."""
        now = datetime.now(timezone.utc)

        # Insert posts
        posts_repo.insert_post({
            "x_post_id": "due_post_1",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Due post",
            "author_id": "user_1",
            "author_username": "testuser",
        })
        posts_repo.insert_post({
            "x_post_id": "future_post_1",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Future post",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create review states
        past_date = (now - timedelta(days=1)).isoformat()
        future_date = (now + timedelta(days=1)).isoformat()

        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for)
            VALUES (?, ?)
        """, ("due_post_1", past_date))
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for)
            VALUES (?, ?)
        """, ("future_post_1", future_date))
        temp_db_v5.commit()

        # Get due posts
        due_posts = repo.get_due_posts()

        assert len(due_posts) == 1
        assert due_posts[0]["post_id"] == "due_post_1"

    def test_get_due_posts_with_topic_id_filters_by_post_topics_join(self, temp_db_v5, repo, posts_repo, topics_repo):
        """Test 6: get_due_posts with topic_id filters by post_topics join (SPAC-04)."""
        now = datetime.now(timezone.utc)
        past_date = (now - timedelta(days=1)).isoformat()

        # Insert posts
        posts_repo.insert_post({
            "x_post_id": "topic_post_1",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Post with topic",
            "author_id": "user_1",
            "author_username": "testuser",
        })
        posts_repo.insert_post({
            "x_post_id": "untagged_post_1",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Post without topic",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create topic
        topic_id = topics_repo.create_topic("Programming", "Software development")

        # Assign topic to post
        topics_repo.assign_topic_to_post("topic_post_1", topic_id)

        # Create review states
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for)
            VALUES (?, ?)
        """, ("topic_post_1", past_date))
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for)
            VALUES (?, ?)
        """, ("untagged_post_1", past_date))
        temp_db_v5.commit()

        # Get due posts filtered by topic
        due_posts = repo.get_due_posts(topic_id=topic_id)

        assert len(due_posts) == 1
        assert due_posts[0]["post_id"] == "topic_post_1"

    def test_get_stats_returns_total_due_and_reviewed_counts(self, temp_db_v5, repo, posts_repo):
        """Test 7: get_stats returns total_posts, due_count, reviewed_count (D-12)."""
        now = datetime.now(timezone.utc)
        past_date = (now - timedelta(days=1)).isoformat()
        future_date = (now + timedelta(days=1)).isoformat()

        # Insert posts
        for i in range(3):
            posts_repo.insert_post({
                "x_post_id": f"stats_post_{i}",
                "created_at": "2024-01-01T00:00:00Z",
                "text": f"Stats post {i}",
                "author_id": "user_1",
                "author_username": "testuser",
            })

        # Create review states with different states
        # 2 due (scheduled_for in past)
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for, review_count)
            VALUES (?, ?, ?)
        """, ("stats_post_0", past_date, 0))
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for, review_count)
            VALUES (?, ?, ?)
        """, ("stats_post_1", past_date, 2))  # reviewed twice
        # 1 future
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for, review_count)
            VALUES (?, ?, ?)
        """, ("stats_post_2", future_date, 1))
        temp_db_v5.commit()

        # Get stats
        stats = repo.get_stats()

        assert stats["total_posts"] == 3
        assert stats["due_count"] == 2  # Two posts scheduled in the past
        assert stats["reviewed_count"] == 2  # Two posts have been reviewed at least once

    def test_reset_state_deletes_review_state_for_post(self, temp_db_v5, repo, posts_repo):
        """Test 8: reset_state deletes review state for a post (D-13)."""
        # Insert a post
        posts_repo.insert_post({
            "x_post_id": "reset_post_1",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Post to reset",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create review state
        temp_db_v5.execute("""
            INSERT INTO post_review_state (post_id, scheduled_for)
            VALUES (?, ?)
        """, ("reset_post_1", "2024-01-15T00:00:00Z"))
        temp_db_v5.commit()

        # Verify state exists
        count_before = temp_db_v5.execute(
            "SELECT COUNT(*) FROM post_review_state WHERE post_id = ?",
            ("reset_post_1",)
        ).fetchone()[0]
        assert count_before == 1

        # Reset state
        repo.reset_state("reset_post_1")

        # Verify state deleted
        count_after = temp_db_v5.execute(
            "SELECT COUNT(*) FROM post_review_state WHERE post_id = ?",
            ("reset_post_1",)
        ).fetchone()[0]
        assert count_after == 0

    def test_get_due_posts_returns_all_due_posts_ordered_by_scheduled_for(self, temp_db_v5, repo, posts_repo):
        """Test: get_due_posts returns all due posts ordered by scheduled_for ASC."""
        now = datetime.now(timezone.utc)

        # Insert posts
        for i in range(3):
            posts_repo.insert_post({
                "x_post_id": f"ordered_post_{i}",
                "created_at": "2024-01-01T00:00:00Z",
                "text": f"Ordered post {i}",
                "author_id": "user_1",
                "author_username": "testuser",
            })

        # Create review states with different scheduled_for dates
        # All in the past, different dates
        dates = [
            (now - timedelta(days=3)).isoformat(),
            (now - timedelta(days=1)).isoformat(),
            (now - timedelta(days=2)).isoformat(),
        ]

        for i, date in enumerate(dates):
            temp_db_v5.execute("""
                INSERT INTO post_review_state (post_id, scheduled_for)
                VALUES (?, ?)
            """, (f"ordered_post_{i}", date))
        temp_db_v5.commit()

        # Get due posts
        due_posts = repo.get_due_posts()

        # Should be ordered by scheduled_for ASC (oldest first)
        assert len(due_posts) == 3
        assert due_posts[0]["post_id"] == "ordered_post_0"  # 3 days ago
        assert due_posts[1]["post_id"] == "ordered_post_2"  # 2 days ago
        assert due_posts[2]["post_id"] == "ordered_post_1"  # 1 day ago

    def test_get_due_posts_respects_limit_parameter(self, temp_db_v5, repo, posts_repo):
        """Test: get_due_posts respects limit parameter."""
        now = datetime.now(timezone.utc)
        past_date = (now - timedelta(days=1)).isoformat()

        # Insert posts
        for i in range(10):
            posts_repo.insert_post({
                "x_post_id": f"limit_post_{i}",
                "created_at": "2024-01-01T00:00:00Z",
                "text": f"Limit post {i}",
                "author_id": "user_1",
                "author_username": "testuser",
            })
            temp_db_v5.execute("""
                INSERT INTO post_review_state (post_id, scheduled_for)
                VALUES (?, ?)
            """, (f"limit_post_{i}", past_date))
        temp_db_v5.commit()

        # Get due posts with limit
        due_posts = repo.get_due_posts(limit=5)

        assert len(due_posts) == 5

    def test_create_state_with_all_fields(self, temp_db_v5, repo, posts_repo):
        """Test: create_state accepts all optional fields."""
        posts_repo.insert_post({
            "x_post_id": "full_state_post",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Full state post",
            "author_id": "user_1",
            "author_username": "testuser",
        })

        # Create state with all fields
        state = {
            "post_id": "full_state_post",
            "scheduled_for": "2024-01-15T00:00:00Z",
            "last_reviewed": "2024-01-10T00:00:00Z",
            "review_count": 5,
            "user_preference": "soon",
            "stability": 7.5,
            "difficulty": 3.2,
            "state": 2,
            "step": 1,
            "fsrs_data": '{"key": "value"}',
        }
        repo.create_state(state)

        # Verify all fields
        row = temp_db_v5.execute(
            "SELECT * FROM post_review_state WHERE post_id = ?",
            ("full_state_post",)
        ).fetchone()

        assert row["scheduled_for"] == "2024-01-15T00:00:00Z"
        assert row["last_reviewed"] == "2024-01-10T00:00:00Z"
        assert row["review_count"] == 5
        assert row["user_preference"] == "soon"
        assert row["stability"] == 7.5
        assert row["difficulty"] == 3.2
        assert row["state"] == 2
        assert row["step"] == 1
        assert row["fsrs_data"] == '{"key": "value"}'