"""Database initialization and connection management.

Provides:
- init_database: Create database with schema and return connection
- get_connection: Create properly configured SQLite connection

Usage:
    from src.db import init_database

    conn = init_database()  # Creates data/bookmarks.db with schema
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

from .connection import get_connection
from .schema import SCHEMA_V1


def init_database(db_path: Optional[Union[Path, str]] = None) -> sqlite3.Connection:
    """Initialize database with schema and return connection.

    Creates the data/ directory if needed, applies SCHEMA_V1 to create
    users and tokens tables, and returns a connection with proper PRAGMAs.

    Args:
        db_path: Optional path to database file. Defaults to data/bookmarks.db
                 or Settings.database_path if available.

    Returns:
        sqlite3.Connection: Connection with WAL mode, foreign keys enabled,
                           and schema applied.

    Example:
        >>> conn = init_database()
        >>> conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        >>> tables = [row['name'] for row in conn.fetchall()]
        >>> 'users' in tables and 'tokens' in tables
        True

    D-02: Database defaults to data/bookmarks.db.
    D-03: Phase 1 creates users and tokens tables only.
    """
    if db_path is None:
        # Try to get path from Settings, fall back to default
        try:
            from ..config.settings import Settings
            settings = Settings()
            db_path = settings.database_path
        except Exception:
            # Settings not configured or missing required fields
            db_path = Path("data/bookmarks.db")

    db_path = Path(db_path)

    # Create data/ directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Get connection with PRAGMAs applied
    conn = get_connection(db_path)

    # Apply schema
    conn.executescript(SCHEMA_V1)
    conn.commit()

    return conn


__all__ = ["init_database", "get_connection", "SCHEMA_V1"]