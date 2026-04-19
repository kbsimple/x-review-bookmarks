"""Shared pytest fixtures for x-bookmarked-posts tests."""

import pytest
import tempfile
import sqlite3
from pathlib import Path


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