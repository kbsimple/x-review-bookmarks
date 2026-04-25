"""Shared pytest fixtures for x-bookmarked-posts tests."""

import pytest
import tempfile
import sqlite3
from pathlib import Path


# Phase 4 schema tables for tags, topics, and embeddings
SCHEMA_V4_TABLES = """
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_tags (
    post_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS post_topics (
    post_id TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    confidence REAL,
    source TEXT DEFAULT 'user',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, topic_id),
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pending_topic_assignments (
    id INTEGER PRIMARY KEY,
    post_id TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    confidence REAL NOT NULL,
    suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS post_embeddings (
    post_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing.

    Yields:
        sqlite3.Connection: Connection with WAL mode and foreign keys enabled.
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

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_token_file():
    """Create a temporary token file path for testing.

    Yields:
        Path: Path to a temporary file location.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        token_path = Path(f.name)

    yield token_path

    token_path.unlink(missing_ok=True)


@pytest.fixture
def mock_settings(temp_token_file, temp_db):
    """Create mock Settings for testing.

    Yields:
        Settings: Mock settings with test credentials and paths.
    """
    # Import here to avoid circular imports during fixture registration
    # This fixture will work after src/config/settings.py is created
    from pydantic import SecretStr
    from pydantic_settings import BaseSettings

    class MockSettings(BaseSettings):
        client_id: str = "test_client_id"
        client_secret: SecretStr = SecretStr("test_client_secret")
        access_token: str = "test_access_token"
        refresh_token: str = "test_refresh_token"
        token_path: Path = temp_token_file

        # Override database_path to use temp_db
        # Note: temp_db yields a connection, so we'll use a separate path
        database_path: Path = temp_token_file.parent / "test_bookmarks.db"

    return MockSettings()


@pytest.fixture
def mock_auth():
    """Create mock XAuth for testing OAuth functions.

    Yields:
        dict: Mock authentication data with test tokens.
    """
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
    }


@pytest.fixture
def mock_tweepy_client():
    """Create mock tweepy.Client for testing X API calls.

    Yields:
        MagicMock: Mock client with get_bookmarks method.
    """
    from unittest.mock import MagicMock

    client = MagicMock()
    client.get_bookmarks = MagicMock()
    client.last_response = MagicMock()
    client.last_response.headers = {
        "x-rate-limit-remaining": "180",
        "x-rate-limit-reset": "900",
    }
    return client


# ============================================================================
# Phase 4 Fixtures: Tags, Topics, Embeddings
# ============================================================================


@pytest.fixture
def temp_db_v4(temp_db):
    """Create a temporary SQLite database with Phase 4 schema tables.

    Extends temp_db with tags, topics, and embeddings tables.

    Yields:
        sqlite3.Connection: Connection with v4 schema tables created.
    """
    # Create posts table first (required for foreign keys)
    temp_db.execute("""
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

    # Create Phase 4 tables
    temp_db.executescript(SCHEMA_V4_TABLES)
    temp_db.commit()

    yield temp_db


@pytest.fixture
def sample_tags():
    """Return sample tag data for testing.

    Returns:
        list[dict]: List of sample tag dictionaries.
    """
    return [
        {"id": 1, "name": "python"},
        {"id": 2, "name": "ml"},
        {"id": 3, "name": "career"},
    ]


@pytest.fixture
def sample_topics():
    """Return sample topic data for testing.

    Returns:
        list[dict]: List of sample topic dictionaries.
    """
    return [
        {"id": 1, "name": "Programming", "description": "Software development"},
        {"id": 2, "name": "Machine Learning", "description": "AI/ML content"},
        {"id": 3, "name": "Career", "description": "Career advice and insights"},
    ]


@pytest.fixture
def sample_post_with_text():
    """Return a sample post with text content suitable for embedding.

    Returns:
        dict: Sample post dictionary with text content.
    """
    return {
        "x_post_id": "test_post_123",
        "created_at": "2024-01-15T10:30:00Z",
        "text": "Python is a great language for machine learning. "
                "The scikit-learn library makes it easy to build models.",
        "author_id": "user_456",
        "author_username": "mldeveloper",
        "author_display_name": "ML Developer",
        "media_urls": [],
        "link_urls": ["https://scikit-learn.org/"],
        "bookmarked_at": "2024-01-16T08:00:00Z",
    }