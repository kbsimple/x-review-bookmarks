"""Tests for SearchService.

Tests for:
- Full-text search within stored post content (SRCH-01)
- Search by author name or username (SRCH-02)
- Search results with context display (SRCH-03)
"""

import pytest
import sqlite3
from pathlib import Path
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_with_search():
    """Create a temporary database with v3 schema and test posts for search.

    Yields:
        sqlite3.Connection: Connection with posts_fts and sample data.
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

    # Create posts table with v3 schema
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

    # Create FTS5 virtual table
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
            text,
            author_username,
            author_display_name,
            content='posts',
            content_rowid='rowid'
        )
    """)

    # Create FTS5 sync triggers
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
            INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
            VALUES (new.rowid, new.text, new.author_username, new.author_display_name);
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
            INSERT INTO posts_fts(posts_fts, rowid, text, author_username, author_display_name)
            VALUES ('delete', old.rowid, old.text, old.author_username, old.author_display_name);
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
            INSERT INTO posts_fts(posts_fts, rowid, text, author_username, author_display_name)
            VALUES ('delete', old.rowid, old.text, old.author_username, old.author_display_name);
            INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
            VALUES (new.rowid, new.text, new.author_username, new.author_display_name);
        END
    """)

    conn.commit()

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_db_with_sample_posts(temp_db_with_search):
    """Create a database with sample posts for search testing.

    Yields:
        sqlite3.Connection: Connection with sample posts inserted.
    """
    conn = temp_db_with_search

    # Insert sample posts with different authors and content
    sample_posts = [
        {
            "x_post_id": "post_1",
            "created_at": "2024-01-15T10:00:00Z",
            "text": "Python is a great programming language for data science",
            "author_id": "user_1",
            "author_username": "pythonista",
            "author_display_name": "Python Developer",
        },
        {
            "x_post_id": "post_2",
            "created_at": "2024-01-15T11:00:00Z",
            "text": "Learning machine learning with Python and TensorFlow",
            "author_id": "user_2",
            "author_username": "mldev",
            "author_display_name": "ML Engineer",
        },
        {
            "x_post_id": "post_3",
            "created_at": "2024-01-15T12:00:00Z",
            "text": "Web development with Flask and Django frameworks",
            "author_id": "user_1",
            "author_username": "pythonista",
            "author_display_name": "Python Developer",
        },
        {
            "x_post_id": "post_4",
            "created_at": "2024-01-15T13:00:00Z",
            "text": "Software engineering best practices and code quality",
            "author_id": "user_3",
            "author_username": "codecraft",
            "author_display_name": "Code Crafter",
        },
        {
            "x_post_id": "post_5",
            "created_at": "2024-01-15T14:00:00Z",
            "text": "Exact phrase matching test case",
            "author_id": "user_1",
            "author_username": "pythonista",
            "author_display_name": "Python Developer",
        },
    ]

    for post in sample_posts:
        conn.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username, author_display_name
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                post["x_post_id"],
                post["created_at"],
                post["text"],
                post["author_id"],
                post["author_username"],
                post["author_display_name"],
            )
        )

    conn.commit()

    yield conn


class TestSearchServiceInit:
    """Tests for SearchService initialization."""

    def test_init_accepts_connection(self, temp_db_with_search):
        """SearchService.__init__() accepts sqlite3.Connection."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_search)
        assert service is not None

    def test_init_stores_connection(self, temp_db_with_search):
        """SearchService stores connection for later use."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_search)
        assert service._conn is temp_db_with_search


class TestSearchServiceSearch:
    """Tests for SearchService.search() method."""

    def test_search_returns_list(self, temp_db_with_sample_posts):
        """SearchService.search() returns list of SearchResult."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("Python")

        assert isinstance(results, list)

    def test_search_returns_search_result_objects(self, temp_db_with_sample_posts):
        """search() returns list of SearchResult objects with correct fields."""
        from src.services.search import SearchService, SearchResult

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("Python")

        assert len(results) > 0
        result = results[0]
        assert isinstance(result, SearchResult)
        assert hasattr(result, 'x_post_id')
        assert hasattr(result, 'author_username')
        assert hasattr(result, 'author_display_name')
        assert hasattr(result, 'created_at')
        assert hasattr(result, 'snippet')
        assert hasattr(result, 'rank')

    def test_search_uses_bm25_ranking(self, temp_db_with_sample_posts):
        """search() uses bm25() for relevance ranking."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("Python")

        # Results should be ordered by rank (lower is better)
        assert len(results) >= 2
        for i in range(len(results) - 1):
            assert results[i].rank <= results[i + 1].rank

    def test_search_by_content_matches_text_column(self, temp_db_with_sample_posts):
        """search() with 'Python' matches posts containing Python in text."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("Python")

        # Should find posts with Python in text
        assert len(results) >= 2
        post_ids = {r.x_post_id for r in results}
        assert "post_1" in post_ids  # "Python is a great programming language..."

    def test_search_empty_query_returns_empty_list(self, temp_db_with_sample_posts):
        """search() with empty query returns empty list."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)

        # Empty query should return empty list
        results = service.search("")
        assert results == []

        # Whitespace-only query should return empty list
        results = service.search("   ")
        assert results == []

    def test_search_sanitizes_special_characters(self, temp_db_with_sample_posts):
        """search() escapes FTS5 special characters to prevent syntax errors."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)

        # These should not raise errors
        results = service.search("test (case)")
        assert isinstance(results, list)

        results = service.search("test*query")
        assert isinstance(results, list)

        results = service.search("test-query")
        assert isinstance(results, list)

    def test_search_with_limit(self, temp_db_with_sample_posts):
        """search() respects limit parameter."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)

        # Insert more posts to exceed limit
        for i in range(10):
            temp_db_with_sample_posts.execute(
                """
                INSERT INTO posts (
                    x_post_id, created_at, text, author_id, author_username
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (f"limit_test_{i}", "2024-01-16T10:00:00Z", f"Python test {i}", "user_limit", "limiter")
            )
        temp_db_with_sample_posts.commit()

        results = service.search("Python", limit=3)
        assert len(results) == 3

    def test_search_no_match_returns_empty(self, temp_db_with_sample_posts):
        """search() returns empty list when no matches found."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("nonexistent_term_xyz123")

        assert results == []


class TestSearchByAuthor:
    """Tests for author-specific search functionality."""

    def test_search_by_author_username(self, temp_db_with_sample_posts):
        """search_by_author() finds posts by author_username."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search_by_author("pythonista")

        # Should find all posts by pythonista
        assert len(results) >= 3
        for result in results:
            assert result.author_username == "pythonista" or result.author_display_name == "Python Developer"

    def test_search_by_author_display_name(self, temp_db_with_sample_posts):
        """search_by_author() finds posts by author_display_name."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search_by_author("ML Engineer")

        # Should find posts by ML Engineer display name
        assert len(results) >= 1

    def test_search_combined_query_and_author(self, temp_db_with_sample_posts):
        """search(query, author=...) combines text search with author filter."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("Python", author="pythonista")

        # Should find Python posts by pythonista only
        assert len(results) >= 1
        for result in results:
            # Author filter matches username OR display_name
            assert result.author_username == "pythonista" or "Python" in result.text

    def test_search_by_author_no_match_returns_empty(self, temp_db_with_sample_posts):
        """search_by_author() returns empty list when no author matches."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search_by_author("nonexistent_user_xyz")

        assert results == []


class TestSearchSnippets:
    """Tests for snippet and highlight functionality."""

    def test_search_returns_snippet_with_context(self, temp_db_with_sample_posts):
        """search() returns snippet with ... ellipsis around matched content."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("programming")

        assert len(results) >= 1
        snippet = results[0].snippet
        # Snippet should contain the matched term
        assert "programming" in snippet.lower() or "..." in snippet

    def test_search_snippet_is_truncated(self, temp_db_with_sample_posts):
        """Snippet is truncated to reasonable length."""
        from src.services.search import SearchService

        # Insert a post with long text
        temp_db_with_sample_posts.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "long_post",
                "2024-01-17T10:00:00Z",
                "This is a very long text that contains the search term programming and many other words that should be truncated in the snippet output to keep it readable",
                "user_long",
                "longauthor"
            )
        )
        temp_db_with_sample_posts.commit()

        service = SearchService(temp_db_with_sample_posts)
        results = service.search("programming")

        assert len(results) >= 1
        # Snippet should be reasonably sized
        snippet = results[0].snippet
        assert len(snippet) < 200  # Reasonable snippet length


class TestSearchPhraseQuery:
    """Tests for phrase search functionality."""

    def test_search_phrase_query(self, temp_db_with_sample_posts):
        """search() with quoted phrase matches exact phrase."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_sample_posts)
        results = service.search('"exact phrase matching"')

        # Should find the post with the exact phrase
        assert len(results) >= 1
        post_ids = {r.x_post_id for r in results}
        assert "post_5" in post_ids


class TestFTS5TriggerSync:
    """Tests for FTS5 trigger synchronization."""

    def test_insert_updates_fts_index(self, temp_db_with_search):
        """Inserting a post updates the FTS index."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_search)

        # Insert a post
        temp_db_with_search.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("new_post", "2024-01-18T10:00:00Z", "New post about testing", "user_new", "newuser")
        )
        temp_db_with_search.commit()

        # Search should find it
        results = service.search("testing")
        assert len(results) >= 1
        assert results[0].x_post_id == "new_post"

    def test_update_updates_fts_index(self, temp_db_with_search):
        """Updating a post updates the FTS index."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_search)

        # Insert a post
        temp_db_with_search.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("update_test", "2024-01-18T10:00:00Z", "Original text", "user_u", "updater")
        )
        temp_db_with_search.commit()

        # Update the post
        temp_db_with_search.execute(
            """
            UPDATE posts SET text = ? WHERE x_post_id = ?
            """,
            ("Updated text with uniqueword", "update_test")
        )
        temp_db_with_search.commit()

        # Search should find the updated text
        results = service.search("uniqueword")
        assert len(results) >= 1
        assert results[0].x_post_id == "update_test"

    def test_delete_updates_fts_index(self, temp_db_with_search):
        """Deleting a post removes it from FTS index."""
        from src.services.search import SearchService

        service = SearchService(temp_db_with_search)

        # Insert a post
        temp_db_with_search.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("delete_test", "2024-01-18T10:00:00Z", "Post to be deleted", "user_d", "deleter")
        )
        temp_db_with_search.commit()

        # Verify it's found
        results = service.search("deleted")
        assert len(results) >= 1

        # Delete the post
        temp_db_with_search.execute("DELETE FROM posts WHERE x_post_id = ?", ("delete_test",))
        temp_db_with_search.commit()

        # Search should no longer find it
        results = service.search("deleted")
        assert len(results) == 0