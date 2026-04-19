"""SQLite connection factory with required PRAGMA settings.

Critical: Each PRAGMA must be set on EVERY connection:
- foreign_keys=ON: Enforces referential integrity (OFF by default!)
- journal_mode=WAL: Enables concurrent readers during writes
- synchronous=NORMAL: Safe with WAL, faster than FULL
- busy_timeout=5000: Waits 5s instead of failing on lock contention

STOR-01: WAL mode enabled
STOR-02: Foreign key constraints enabled

Usage:
    from src.db.connection import get_connection

    conn = get_connection()
    # Connection has all PRAGMAs applied
    conn.execute("SELECT * FROM users")
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union


def get_connection(db_path: Optional[Union[Path, str]] = None) -> sqlite3.Connection:
    """Create a SQLite connection with all required PRAGMA settings.

    CRITICAL: Each PRAGMA must be set on EVERY connection because SQLite
    resets some PRAGMAs (especially foreign_keys) on each new connection.

    Args:
        db_path: Path to database file. Defaults to data/bookmarks.db per D-02.

    Returns:
        sqlite3.Connection: Connection with:
            - foreign_keys=ON (STOR-02)
            - journal_mode=WAL (STOR-01)
            - synchronous=NORMAL
            - busy_timeout=5000ms
            - row_factory=sqlite3.Row

    Example:
        >>> conn = get_connection()
        >>> conn.execute("PRAGMA foreign_keys").fetchone()['foreign_keys']
        1
        >>> conn.execute("PRAGMA journal_mode").fetchone()['journal_mode']
        'wal'

    Note:
        journal_mode=WAL persists across connections for the database file,
        but we set it on every connection to ensure consistency.
        foreign_keys=ON must be set on every connection - it does NOT persist.
    """
    if db_path is None:
        # D-02: Default to data/bookmarks.db
        db_path = Path("data/bookmarks.db")

    db_path = Path(db_path)

    # Create connection with timeout for busy situations
    conn = sqlite3.connect(str(db_path), timeout=30.0)

    # Enable Row factory for dict-like access
    conn.row_factory = sqlite3.Row

    # Essential PRAGMAs - MUST be set on every connection

    # STOR-02: Foreign key enforcement (OFF by default - must enable!)
    # This is CRITICAL for data integrity. SQLite does NOT enforce FKs by default.
    conn.execute("PRAGMA foreign_keys = ON")

    # STOR-01: Write-Ahead Logging for concurrent access
    # Allows readers during writes, essential for CLI + background scheduler
    conn.execute("PRAGMA journal_mode = WAL")

    # synchronous=NORMAL is safe with WAL and faster than FULL
    # FULL syncs on every write, NORMAL syncs less aggressively
    conn.execute("PRAGMA synchronous = NORMAL")

    # Wait up to 5 seconds on lock contention instead of failing immediately
    # Important for concurrent access scenarios
    conn.execute("PRAGMA busy_timeout = 5000")

    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for transactions with auto-commit/rollback.

    Usage:
        with transaction(conn) as tx:
            tx.execute("INSERT INTO users ...")
            tx.execute("INSERT INTO tokens ...")
            # Auto-commits on success, auto-rollbacks on exception

    Args:
        conn: SQLite connection to use for transaction.

    Yields:
        The connection for executing statements within the transaction.

    Note:
        This is a convenience wrapper. SQLite transactions are implicit
        (begin on first statement), but this provides explicit commit/rollback.
    """
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise