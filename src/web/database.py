"""FastAPI database dependency with proper connection lifecycle management.

WEB-DB-01: Database connections properly closed in all error paths.
WEB-DB-02: Use Depends() pattern for clean dependency injection.

This module provides a FastAPI dependency that ensures SQLite connections
are always closed, even when exceptions occur. This prevents connection
leaks that can cause "database is locked" errors and resource exhaustion.

Usage:
    from fastapi import Depends
    from src.web.database import get_db

    @router.get("/posts")
    async def get_posts(conn = Depends(get_db)):
        repo = PostsRepository(conn)
        return repo.list_posts()
        # Connection automatically closed after return/exception

The yield pattern ensures the finally block runs even if:
- An exception is raised in the route handler
- An HTTP exception is raised
- The request is cancelled
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union

import sqlite3


async def get_db(db_path: Optional[Union[Path, str]] = None) -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency that yields a database connection and ensures cleanup.

    WEB-DB-01: Guarantees connection is closed even on exceptions.

    This is a FastAPI dependency using the yield pattern. FastAPI will:
    1. Call the function up to yield
    2. Pass the yielded value to the route handler
    3. Resume after yield when the route handler completes (success or exception)

    Args:
        db_path: Optional path to database file. Defaults to data/bookmarks.db.

    Yields:
        sqlite3.Connection: Connection with proper PRAGMAs and schema applied.

    Example:
        @router.get("/posts")
        async def get_posts(conn = Depends(get_db)):
            repo = PostsRepository(conn)
            return repo.list_posts()
            # Connection automatically closed after return

    Note:
        The connection is closed in a finally block, which runs even if:
        - Route handler raises an exception
        - HTTPException is raised (e.g., 404)
        - Request is cancelled
    """
    # Lazy import to allow test mocking of init_database
    from ..db import init_database

    conn = init_database(db_path)
    try:
        yield conn
    finally:
        conn.close()


# For synchronous routes (if needed)
@contextmanager
def get_db_sync(db_path: Optional[Union[Path, str]] = None) -> Generator[sqlite3.Connection, None, None]:
    """Synchronous context manager for database connections.

    Use this for non-FastAPI code that needs database access.

    Args:
        db_path: Optional path to database file.

    Yields:
        sqlite3.Connection: Connection with proper PRAGMAs and schema.

    Example:
        with get_db_sync() as conn:
            repo = PostsRepository(conn)
            posts = repo.list_posts()
        # Connection automatically closed
    """
    # Lazy import to allow test mocking of init_database
    from ..db import init_database

    conn = init_database(db_path)
    try:
        yield conn
    finally:
        conn.close()


__all__ = ["get_db", "get_db_sync"]