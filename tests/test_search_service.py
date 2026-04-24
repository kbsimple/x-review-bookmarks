"""Tests for SearchService.

Tests for:
- Full-text search within stored post content (SRCH-01)
- Search by author name or username (SRCH-02)
- Search results with context display (SRCH-03)

Wave 0 scaffold - tests will be implemented in Wave 2.
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


class TestSearchService:
    """Tests for SearchService FTS5 functionality.

    SRCH-01: Full-text search within stored post content.
    SRCH-02: Search by author name or username.
    SRCH-03: Search results with context display.
    """

    def test_search_returns_results(self, temp_db_with_search):
        """Verify search returns matching posts.

        SRCH-01: Full-text search within stored post content.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_search_by_author(self, temp_db_with_search):
        """Verify search can filter by author.

        SRCH-02: Search by author name or username.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_search_with_snippet(self, temp_db_with_search):
        """Verify search returns highlighted snippets.

        SRCH-03: Search results with context display (snippet highlighting).

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_search_empty_query_returns_empty(self, temp_db_with_search):
        """Verify empty search query returns empty results.

        Edge case: Empty or whitespace-only query.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_search_phrase_query(self, temp_db_with_search):
        """Verify phrase search returns exact matches.

        FTS5 feature: "exact phrase" matching.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_search_with_limit(self, temp_db_with_search):
        """Verify search respects limit parameter.

        Performance: Limit results to avoid overwhelming output.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")