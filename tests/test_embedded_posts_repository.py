"""Tests for EmbeddedPostsRepository - embedded posts CRUD operations.

Tests verify:
- Upsert embedded post (insert new, update existing)
- Get by ID
- Handle unavailable flag for deleted/protected originals

STR-01: Embedded posts stored in separate table.
STR-03: Unavailable originals marked with available=False.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_v6():
    """Create a temporary SQLite database with v6 schema.

    Yields:
        sqlite3.Connection: Connection with v6 schema (embedded_posts table).
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

    # Create posts table (v2 schema)
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
            link_status TEXT DEFAULT 'unchecked',
            post_type TEXT DEFAULT 'original',
            embedded_post_id TEXT
        )
    """)

    # Create embedded_posts table (v6 schema)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embedded_posts (
            x_post_id TEXT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL,
            text TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_username TEXT NOT NULL,
            author_display_name TEXT,
            media_urls TEXT,
            link_urls TEXT,
            available INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


class TestEmbeddedPostsRepository:
    """Tests for EmbeddedPostsRepository CRUD operations.

    STR-01: Embedded posts stored in separate embedded_posts table.
    STR-02: Posts reference embedded posts via embedded_post_id.
    STR-03: Unavailable originals marked with available=False.
    """

    def test_upsert_embedded_post_inserts_new(self, temp_db_v6):
        """Verify upsert_embedded_post inserts new embedded post.

        STR-01: Store embedded post content in embedded_posts table.
        """
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        repo = EmbeddedPostsRepository(temp_db_v6)

        embedded_post = {
            "x_post_id": "embedded_123",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "This is the original tweet content",
            "author_id": "user_456",
            "author_username": "original_author",
            "author_display_name": "Original Author",
            "media_urls": ["https://example.com/image.jpg"],
            "link_urls": ["https://example.com/article"],
            "available": True,
        }

        repo.upsert_embedded_post(embedded_post)

        # Verify insert
        result = repo.get_by_id("embedded_123")
        assert result is not None
        assert result["x_post_id"] == "embedded_123"
        assert result["text"] == "This is the original tweet content"
        assert result["author_username"] == "original_author"
        assert result["available"] is True

    def test_upsert_embedded_post_updates_existing(self, temp_db_v6):
        """Verify upsert_embedded_post updates existing embedded post on conflict.

        STR-01: Upsert should update existing embedded posts on re-sync.
        """
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        repo = EmbeddedPostsRepository(temp_db_v6)

        # Insert initial embedded post
        embedded_v1 = {
            "x_post_id": "embedded_456",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Original text",
            "author_id": "user_789",
            "author_username": "author1",
            "author_display_name": "Author One",
            "available": True,
        }
        repo.upsert_embedded_post(embedded_v1)

        # Upsert with updated text
        embedded_v2 = {
            "x_post_id": "embedded_456",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Updated text",
            "author_id": "user_789",
            "author_username": "author1",
            "author_display_name": "Author One Updated",
            "available": True,
        }
        repo.upsert_embedded_post(embedded_v2)

        # Verify update
        result = repo.get_by_id("embedded_456")
        assert result["text"] == "Updated text"
        assert result["author_display_name"] == "Author One Updated"

    def test_get_by_id_returns_dict(self, temp_db_v6):
        """Verify get_by_id returns embedded post dict with all fields.

        STR-01: Embedded post dict should have all required fields.
        """
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        repo = EmbeddedPostsRepository(temp_db_v6)

        embedded_post = {
            "x_post_id": "embedded_789",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "Test embedded post",
            "author_id": "user_123",
            "author_username": "testuser",
            "author_display_name": "Test User",
            "media_urls": [],
            "link_urls": [],
            "available": True,
        }
        repo.upsert_embedded_post(embedded_post)

        result = repo.get_by_id("embedded_789")

        assert result is not None
        assert "x_post_id" in result
        assert "created_at" in result
        assert "text" in result
        assert "author_id" in result
        assert "author_username" in result
        assert "author_display_name" in result
        assert "media_urls" in result
        assert "link_urls" in result
        assert "available" in result

        assert result["x_post_id"] == "embedded_789"
        assert result["text"] == "Test embedded post"
        assert result["author_username"] == "testuser"

    def test_get_by_id_returns_none_for_nonexistent(self, temp_db_v6):
        """Verify get_by_id returns None for non-existent embedded post.

        STR-01: Should return None gracefully for unknown posts.
        """
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        repo = EmbeddedPostsRepository(temp_db_v6)

        result = repo.get_by_id("nonexistent_id")

        assert result is None

    def test_upsert_embedded_post_handles_unavailable(self, temp_db_v6):
        """Verify upsert_embedded_post handles unavailable flag correctly.

        STR-03: Embedded posts from deleted/protected originals marked unavailable.
        """
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        repo = EmbeddedPostsRepository(temp_db_v6)

        # Insert embedded post as unavailable (deleted original)
        unavailable_post = {
            "x_post_id": "embedded_unavailable",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "",  # Empty text for unavailable
            "author_id": "",
            "author_username": "",
            "author_display_name": None,
            "media_urls": [],
            "link_urls": [],
            "available": False,  # Marked as unavailable
        }
        repo.upsert_embedded_post(unavailable_post)

        # Verify unavailable flag stored correctly
        result = repo.get_by_id("embedded_unavailable")
        assert result is not None
        assert result["available"] is False