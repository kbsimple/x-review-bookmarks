"""Tests for posts repository.

Tests for:
- Insert post
- Upsert post
- Get by ID
- Get all posts
- Incremental sync queries
"""

import pytest
import sqlite3
from pathlib import Path
import sys
from unittest.mock import MagicMock
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_with_schema():
    """Create a temporary SQLite database with posts table schema (v3).

    Yields:
        sqlite3.Connection: Connection with posts table created and v3 schema.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Apply required PRAGMAs
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    # Create posts table schema per D-01
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            x_post_id TEXT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL,
            text TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_username TEXT NOT NULL,
            author_display_name TEXT,
            media_urls TEXT,
            link_urls TEXT,
            bookmarked_at TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_version INTEGER DEFAULT 1,
            note TEXT,
            link_status TEXT DEFAULT 'unchecked'
        )
    """)
    conn.commit()

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


class TestPostsRepository:
    """Tests for PostsRepository CRUD operations."""

    def test_insert_post_stores_data(self, temp_db_with_schema):
        """Verify post can be inserted into database.

        DATA-02: Store posts with full content (text, author, images, links, media).
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        post = {
            "x_post_id": "tweet_123",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Hello world! This is a test post.",
            "author_id": "user_456",
            "author_username": "testuser",
            "author_display_name": "Test User",
            "media_urls": ["https://example.com/image1.jpg"],
            "link_urls": ["https://example.com/article"],
            "bookmarked_at": "2024-01-16T08:00:00Z",
        }

        repo.insert_post(post)

        # Verify insert
        result = repo.get_by_id("tweet_123")
        assert result is not None
        assert result["x_post_id"] == "tweet_123"
        assert result["text"] == "Hello world! This is a test post."
        assert result["author_username"] == "testuser"
        assert result["media_urls"] == ["https://example.com/image1.jpg"]
        assert result["link_urls"] == ["https://example.com/article"]

    def test_upsert_post_updates_existing(self, temp_db_with_schema):
        """Verify upsert updates existing post and increments sync_version.

        DATA-02: Upsert should update existing posts on re-sync.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert initial post
        post_v1 = {
            "x_post_id": "tweet_123",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Original text",
            "author_id": "user_456",
            "author_username": "testuser",
        }
        repo.upsert_post(post_v1)

        # Upsert with updated text
        post_v2 = {
            "x_post_id": "tweet_123",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Updated text",
            "author_id": "user_456",
            "author_username": "testuser",
        }
        repo.upsert_post(post_v2)

        # Verify update
        result = repo.get_by_id("tweet_123")
        assert result["text"] == "Updated text"
        assert result["sync_version"] == 2  # Incremented from 1 to 2

    def test_upsert_post_inserts_new(self, temp_db_with_schema):
        """Verify upsert inserts new post if not exists."""
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        post = {
            "x_post_id": "new_tweet_789",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "New post",
            "author_id": "user_456",
            "author_username": "testuser",
        }
        repo.upsert_post(post)

        result = repo.get_by_id("new_tweet_789")
        assert result is not None
        assert result["text"] == "New post"
        assert result["sync_version"] == 1

    def test_get_all_returns_ordered_by_created_at_desc(self, temp_db_with_schema):
        """Verify get_all returns posts ordered by created_at descending.

        DATA-03: Store publication date for each post.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert 3 posts with different dates
        posts = [
            {
                "x_post_id": "old_post",
                "created_at": "2024-01-01T00:00:00Z",
                "text": "Oldest post",
                "author_id": "user_1",
                "author_username": "user1",
            },
            {
                "x_post_id": "new_post",
                "created_at": "2024-01-15T00:00:00Z",
                "text": "Newest post",
                "author_id": "user_1",
                "author_username": "user1",
            },
            {
                "x_post_id": "mid_post",
                "created_at": "2024-01-08T00:00:00Z",
                "text": "Middle post",
                "author_id": "user_1",
                "author_username": "user1",
            },
        ]
        for post in posts:
            repo.insert_post(post)

        results = repo.get_all()

        assert len(results) == 3
        # Should be ordered newest first
        assert results[0]["x_post_id"] == "new_post"
        assert results[1]["x_post_id"] == "mid_post"
        assert results[2]["x_post_id"] == "old_post"

    def test_count_returns_correct(self, temp_db_with_schema):
        """Verify count returns total number of posts."""
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert 5 posts
        for i in range(5):
            repo.insert_post({
                "x_post_id": f"tweet_{i}",
                "created_at": f"2024-01-{10+i:02d}T00:00:00Z",
                "text": f"Post {i}",
                "author_id": "user_1",
                "author_username": "user1",
            })

        assert repo.count() == 5

    def test_get_by_id_returns_none_if_not_found(self, temp_db_with_schema):
        """Verify get_by_id returns None for non-existent post."""
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        result = repo.get_by_id("nonexistent")
        assert result is None

    def test_get_all_with_limit_and_offset(self, temp_db_with_schema):
        """Verify get_all respects limit and offset for pagination."""
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert 10 posts
        for i in range(10):
            repo.insert_post({
                "x_post_id": f"tweet_{i:02d}",
                "created_at": f"2024-01-{i+1:02d}T00:00:00Z",
                "text": f"Post {i}",
                "author_id": "user_1",
                "author_username": "user1",
            })

        # Get first page
        page1 = repo.get_all(limit=5, offset=0)
        assert len(page1) == 5

        # Get second page
        page2 = repo.get_all(limit=5, offset=5)
        assert len(page2) == 5

        # Verify no overlap
        page1_ids = {p["x_post_id"] for p in page1}
        page2_ids = {p["x_post_id"] for p in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestPostsRepositoryNoteAndLinkStatus:
    """Tests for note and link_status columns added in Phase 3.

    NOTE-01: User can add personal notes to bookmarked posts.
    NOTE-02: Notes displayed when post is resurfaced for review.
    MAINT-01: Application detects and flags dead links.
    MAINT-02: Application can filter dead links from review queue.
    """

    def test_update_note_sets_note_text(self, temp_db_with_schema):
        """Verify update_note sets note column for a post.

        NOTE-01: User can add personal notes to bookmarked posts.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert a post first
        post = {
            "x_post_id": "note_test_1",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post for note",
            "author_id": "user_1",
            "author_username": "testuser",
        }
        repo.insert_post(post)

        # Update note
        repo.update_note("note_test_1", "This is my personal note")

        # Verify note was set
        result = repo.get_by_id("note_test_1")
        assert result["note"] == "This is my personal note"

    def test_update_note_sets_null_when_none(self, temp_db_with_schema):
        """Verify update_note sets NULL when note is None.

        NOTE-01: User can clear notes by passing None.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert a post with a note
        post = {
            "x_post_id": "note_clear_test",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post",
            "author_id": "user_1",
            "author_username": "testuser",
        }
        repo.insert_post(post)
        repo.update_note("note_clear_test", "Initial note")

        # Clear the note
        repo.update_note("note_clear_test", None)

        # Verify note is None
        result = repo.get_by_id("note_clear_test")
        assert result["note"] is None

    def test_get_by_id_returns_note_field(self, temp_db_with_schema):
        """Verify get_by_id returns note field in dict.

        NOTE-02: Notes displayed when post is resurfaced for review.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        post = {
            "x_post_id": "note_field_test",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post",
            "author_id": "user_1",
            "author_username": "testuser",
        }
        repo.insert_post(post)
        repo.update_note("note_field_test", "My note")

        result = repo.get_by_id("note_field_test")
        assert "note" in result
        assert result["note"] == "My note"

    def test_update_link_status_sets_status(self, temp_db_with_schema):
        """Verify update_link_status sets link_status column.

        MAINT-01: Application detects and flags dead links.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        post = {
            "x_post_id": "link_status_test",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post with link",
            "author_id": "user_1",
            "author_username": "testuser",
            "link_urls": ["https://example.com/article"],
        }
        repo.insert_post(post)

        # Update link status
        repo.update_link_status("link_status_test", "ok")

        result = repo.get_by_id("link_status_test")
        assert result["link_status"] == "ok"

    def test_update_link_status_sets_dead(self, temp_db_with_schema):
        """Verify update_link_status can mark links as dead.

        MAINT-01: Application detects and flags dead links.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        post = {
            "x_post_id": "dead_link_test",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post with dead link",
            "author_id": "user_1",
            "author_username": "testuser",
            "link_urls": ["https://example.com/dead"],
        }
        repo.insert_post(post)

        # Mark link as dead
        repo.update_link_status("dead_link_test", "dead")

        result = repo.get_by_id("dead_link_test")
        assert result["link_status"] == "dead"

    def test_get_posts_with_links_returns_posts_with_links(self, temp_db_with_schema):
        """Verify get_posts_with_links returns only posts with links.

        MAINT-01: Application needs to check links in stored posts.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert posts - some with links, some without
        posts = [
            {
                "x_post_id": "with_links_1",
                "created_at": "2024-01-15T10:30:00Z",
                "text": "Post with link",
                "author_id": "user_1",
                "author_username": "testuser",
                "link_urls": ["https://example.com/1"],
            },
            {
                "x_post_id": "no_links",
                "created_at": "2024-01-15T11:00:00Z",
                "text": "Post without link",
                "author_id": "user_1",
                "author_username": "testuser",
                "link_urls": [],
            },
            {
                "x_post_id": "with_links_2",
                "created_at": "2024-01-15T12:00:00Z",
                "text": "Another post with link",
                "author_id": "user_1",
                "author_username": "testuser",
                "link_urls": ["https://example.com/2", "https://example.com/3"],
            },
        ]
        for post in posts:
            repo.insert_post(post)

        results = repo.get_posts_with_links()

        # Should return only posts with links
        assert len(results) == 2
        post_ids = {r["x_post_id"] for r in results}
        assert "with_links_1" in post_ids
        assert "with_links_2" in post_ids
        assert "no_links" not in post_ids

    def test_get_posts_exclude_dead_links_filters_dead(self, temp_db_with_schema):
        """Verify get_posts_exclude_dead_links excludes posts with dead links.

        MAINT-02: Application can filter dead links from review queue.
        """
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        # Insert posts with different link statuses
        posts = [
            {
                "x_post_id": "unchecked_link",
                "created_at": "2024-01-15T10:30:00Z",
                "text": "Post with unchecked link",
                "author_id": "user_1",
                "author_username": "testuser",
                "link_urls": ["https://example.com/unchecked"],
            },
            {
                "x_post_id": "dead_link",
                "created_at": "2024-01-15T11:00:00Z",
                "text": "Post with dead link",
                "author_id": "user_1",
                "author_username": "testuser",
                "link_urls": ["https://example.com/dead"],
            },
            {
                "x_post_id": "ok_link",
                "created_at": "2024-01-15T12:00:00Z",
                "text": "Post with ok link",
                "author_id": "user_1",
                "author_username": "testuser",
                "link_urls": ["https://example.com/ok"],
            },
        ]
        for post in posts:
            repo.insert_post(post)

        # Update link statuses
        repo.update_link_status("unchecked_link", "unchecked")
        repo.update_link_status("dead_link", "dead")
        repo.update_link_status("ok_link", "ok")

        results = repo.get_posts_exclude_dead_links()

        # Should exclude posts with dead links
        post_ids = {r["x_post_id"] for r in results}
        assert "dead_link" not in post_ids
        assert "unchecked_link" in post_ids
        assert "ok_link" in post_ids

    def test_row_to_dict_includes_note_and_link_status(self, temp_db_with_schema):
        """Verify _row_to_dict includes note and link_status fields."""
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_schema)

        post = {
            "x_post_id": "fields_test",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test post",
            "author_id": "user_1",
            "author_username": "testuser",
        }
        repo.insert_post(post)
        repo.update_note("fields_test", "Test note")
        repo.update_link_status("fields_test", "ok")

        result = repo.get_by_id("fields_test")
        assert "note" in result
        assert "link_status" in result
        assert result["note"] == "Test note"
        assert result["link_status"] == "ok"