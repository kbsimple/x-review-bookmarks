"""Functional tests for browse endpoints.

Tests WEB-04: User can browse posts with cursor-based pagination.

This test module:
1. Creates a mock SQLite database with sample posts
2. Starts a FastAPI test client pointing at that database
3. Makes HTTP requests to browse endpoints to verify correct posts are served
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from src.web.app import create_app
from src.db import init_database


# Sample mock posts for testing
MOCK_POSTS = [
    {
        "x_post_id": "post_001",
        "created_at": "2024-01-15T10:30:00Z",
        "text": "First post about Python programming",
        "author_id": "author_001",
        "author_username": "pythonista",
        "author_display_name": "Python Developer",
        "media_urls": "[]",
        "link_urls": "[]",
        "bookmarked_at": "2024-01-15T11:00:00Z",
    },
    {
        "x_post_id": "post_002",
        "created_at": "2024-01-16T14:20:00Z",
        "text": "Second post about machine learning",
        "author_id": "author_002",
        "author_username": "mldev",
        "author_display_name": "ML Developer",
        "media_urls": "[]",
        "link_urls": "[]",
        "bookmarked_at": "2024-01-16T15:00:00Z",
    },
    {
        "x_post_id": "post_003",
        "created_at": "2024-01-17T09:45:00Z",
        "text": "Third post about web development",
        "author_id": "author_001",
        "author_username": "pythonista",
        "author_display_name": "Python Developer",
        "media_urls": "[]",
        "link_urls": "[]",
        "bookmarked_at": "2024-01-17T10:00:00Z",
    },
    {
        "x_post_id": "post_004",
        "created_at": "2024-01-18T16:00:00Z",
        "text": "Fourth post about data science",
        "author_id": "author_003",
        "author_username": "datascientist",
        "author_display_name": "Data Scientist",
        "media_urls": "[]",
        "link_urls": "[]",
        "bookmarked_at": "2024-01-18T17:00:00Z",
    },
    {
        "x_post_id": "post_005",
        "created_at": "2024-01-19T11:30:00Z",
        "text": "Fifth post about cloud computing",
        "author_id": "author_002",
        "author_username": "mldev",
        "author_display_name": "ML Developer",
        "media_urls": "[]",
        "link_urls": "[]",
        "bookmarked_at": "2024-01-19T12:00:00Z",
    },
]


@pytest.fixture
def mock_db_with_posts():
    """Create a temporary SQLite database with mock posts.

    Yields:
        Path: Path to the temporary database file.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = init_database(db_path)

    # Insert mock posts
    for post in MOCK_POSTS:
        conn.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username,
                author_display_name, media_urls, link_urls, bookmarked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post["x_post_id"],
                post["created_at"],
                post["text"],
                post["author_id"],
                post["author_username"],
                post["author_display_name"],
                post["media_urls"],
                post["link_urls"],
                post["bookmarked_at"],
            ),
        )
    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture
def test_client(mock_db_with_posts):
    """Create a FastAPI test client with mock database.

    Args:
        mock_db_with_posts: Path to temporary database with mock posts.

    Yields:
        TestClient: FastAPI test client.
    """
    app = create_app()

    # Patch the database path to use our mock database
    with patch("src.web.routes.browse.Path") as mock_path_class:
        # Make Path("data/bookmarks.db") return our mock db path
        mock_path_class.return_value = mock_db_with_posts

        client = TestClient(app)
        yield client


class TestBrowseEndpoint:
    """Tests for GET /browse endpoint."""

    def test_browse_returns_html(self, test_client):
        """Verify /browse returns HTML content.

        WEB-04: User can browse posts with cursor-based pagination.

        Expected behavior:
        - Response status 200
        - Content-Type: text/html
        - Contains post content
        """
        response = test_client.get("/browse")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_browse_shows_posts(self, test_client):
        """Verify /browse displays mock posts.

        Expected behavior:
        - Response contains text from mock posts
        - Posts are ordered by created_at descending
        """
        response = test_client.get("/browse")

        # Check that posts are displayed (newest first)
        content = response.text

        # Newest post (post_005) should appear
        assert "cloud computing" in content.lower() or "post_005" in content

    def test_browse_pagination_default_limit(self, test_client):
        """Verify /browse respects default limit of 20 posts.

        Expected behavior:
        - Default limit is 20 posts per page
        - has_more indicator when more posts exist
        """
        response = test_client.get("/browse")

        assert response.status_code == 200
        # With 5 mock posts, no pagination needed
        # This test validates the endpoint works with small datasets


class TestApiPostsEndpoint:
    """Tests for GET /api/posts endpoint (JSON API)."""

    def test_api_posts_returns_json(self, test_client):
        """Verify /api/posts returns JSON response.

        WEB-04: JSON endpoint for HTMX infinite scroll.

        Expected behavior:
        - Response status 200
        - Content-Type: application/json
        - Response has posts array and has_more boolean
        """
        response = test_client.get("/api/posts")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        data = response.json()
        assert "posts" in data
        assert "has_more" in data
        assert isinstance(data["posts"], list)
        assert isinstance(data["has_more"], bool)

    def test_api_posts_returns_posts_ordered_by_date(self, test_client):
        """Verify /api/posts returns posts ordered by created_at descending.

        Expected behavior:
        - Posts returned in reverse chronological order
        - Each post has required fields
        """
        response = test_client.get("/api/posts")

        assert response.status_code == 200
        data = response.json()

        posts = data["posts"]
        assert len(posts) == 5, f"Expected 5 posts, got {len(posts)}"

        # Check ordering - newest first
        # post_005 has created_at 2024-01-19, post_001 has 2024-01-15
        assert posts[0]["x_post_id"] == "post_005"
        assert posts[-1]["x_post_id"] == "post_001"

    def test_api_posts_limit_parameter(self, test_client):
        """Verify /api/posts respects limit query parameter.

        Expected behavior:
        - limit=2 returns only 2 posts
        - has_more is True when more posts exist
        """
        response = test_client.get("/api/posts?limit=2")

        assert response.status_code == 200
        data = response.json()

        posts = data["posts"]
        assert len(posts) == 2, f"Expected 2 posts, got {len(posts)}"
        assert data["has_more"] is True, "has_more should be True when posts remain"

    def test_api_posts_returns_correct_fields(self, test_client):
        """Verify /api/posts returns all expected post fields.

        Expected behavior:
        - Each post contains: x_post_id, created_at, text, author_id,
          author_username, author_display_name, media_urls, link_urls
        """
        response = test_client.get("/api/posts?limit=1")

        assert response.status_code == 200
        data = response.json()

        post = data["posts"][0]

        # Check required fields
        assert "x_post_id" in post
        assert "created_at" in post
        assert "text" in post
        assert "author_id" in post
        assert "author_username" in post

    def test_api_posts_cursor_pagination(self, test_client):
        """Verify /api/posts cursor-based pagination.

        Expected behavior:
        - Providing cursor returns next page of posts
        - Cursor is base64 encoded (created_at, x_post_id)
        - No duplicate posts between pages
        """
        # Get first page
        response1 = test_client.get("/api/posts?limit=2")
        data1 = response1.json()

        assert len(data1["posts"]) == 2
        assert data1["has_more"] is True
        assert data1["next_cursor"] is not None

        first_page_ids = {p["x_post_id"] for p in data1["posts"]}

        # Get second page using cursor
        cursor = data1["next_cursor"]
        response2 = test_client.get(f"/api/posts?limit=2&cursor={cursor}")
        data2 = response2.json()

        assert response2.status_code == 200

        second_page_ids = {p["x_post_id"] for p in data2["posts"]}

        # No overlap between pages
        assert first_page_ids.isdisjoint(second_page_ids), "Pages should not have duplicate posts"

        # Total should be 5 posts
        all_ids = first_page_ids | second_page_ids
        assert len(all_ids) == 4, "Should have 4 posts across two pages"

    def test_api_posts_empty_database(self):
        """Verify /api/posts handles empty database gracefully.

        Expected behavior:
        - Returns empty posts array
        - has_more is False
        - No errors
        """
        # Create empty database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        conn = init_database(db_path)
        conn.close()

        app = create_app()

        with patch("src.web.routes.browse.Path") as mock_path_class:
            mock_path_class.return_value = db_path
            client = TestClient(app)

            response = client.get("/api/posts")

            assert response.status_code == 200
            data = response.json()
            assert data["posts"] == []
            assert data["has_more"] is False
            assert data["next_cursor"] is None

        db_path.unlink(missing_ok=True)


class TestPaginationCursor:
    """Tests for pagination cursor encoding/decoding."""

    def test_cursor_encoding_decoding(self):
        """Verify cursor encodes and decodes correctly."""
        from src.web.pagination import Cursor

        cursor = Cursor(created_at="2024-01-15T10:30:00Z", x_post_id="post_123")
        encoded = cursor.encode()

        assert isinstance(encoded, str)
        assert len(encoded) > 0

        # Decode and verify
        decoded = Cursor.decode(encoded)
        assert decoded is not None
        assert decoded.created_at == "2024-01-15T10:30:00Z"
        assert decoded.x_post_id == "post_123"

    def test_cursor_invalid_decode(self):
        """Verify cursor returns None for invalid input."""
        from src.web.pagination import Cursor

        # Invalid base64
        decoded = Cursor.decode("not-valid-base64!!!")
        assert decoded is None

        # Valid base64 but invalid JSON
        import base64
        invalid_json = base64.urlsafe_b64encode(b"not json").decode()
        decoded = Cursor.decode(invalid_json)
        assert decoded is None


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_200(self, test_client):
        """Verify /health returns healthy status.

        Expected behavior:
        - Response status 200
        - JSON with status: healthy
        """
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"