"""Database schema migrations for x-bookmarked-posts.

Handles incremental schema upgrades using PRAGMA user_version tracking.

Migration versions:
- v1: Initial schema (users, tokens tables)
- v2: Posts and sync_state tables
- v3: FTS5 virtual table, note column, link_status column

Usage:
    from src.db.migrations import run_migrations, get_schema_version_int

    conn = get_connection()
    run_migrations(conn)  # Applies all pending migrations
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from .schema import SCHEMA_V3_MIGRATION, SCHEMA_V4_MIGRATION, SCHEMA_V5_MIGRATION, SCHEMA_V6_MIGRATION


def get_schema_version_int(conn: sqlite3.Connection) -> int:
    """Get the current schema version as an integer.

    Uses PRAGMA user_version to track schema version.
    Returns 0 if no version has been set (fresh database).

    Args:
        conn: SQLite connection.

    Returns:
        Integer schema version (0, 1, 2, 3, ...)
    """
    result = conn.execute("PRAGMA user_version").fetchone()
    return result[0] if result else 0


def migrate_to_v3(conn: sqlite3.Connection) -> None:
    """Migrate from v2 to v3: Add note, link_status columns and FTS5 table.

    Idempotent: Safe to call multiple times. Checks PRAGMA user_version
    before applying changes.

    SRCH-01: FTS5 virtual table for full-text search.
    NOTE-01: note column for personal notes on posts.
    MAINT-01: link_status column for dead link detection.

    Args:
        conn: SQLite connection.
    """
    current_version = get_schema_version_int(conn)

    # Idempotent: Skip if already at v3 or higher
    if current_version >= 3:
        return

    # Add note column (D-02, NOTE-01, NOTE-02)
    # SQLite doesn't support ALTER TABLE IF NOT EXISTS, so use try/except
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN note TEXT")
    except sqlite3.OperationalError:
        # Column already exists, which is fine for idempotency
        pass

    # Add link_status column (D-04, MAINT-01, MAINT-02)
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN link_status TEXT DEFAULT 'unchecked'")
    except sqlite3.OperationalError:
        # Column already exists, which is fine for idempotency
        pass

    # Commit column additions before creating FTS5 (FTS5 needs columns to exist)
    conn.commit()

    # Create FTS5 virtual table and sync triggers (D-01, SRCH-01)
    # This uses IF NOT EXISTS for idempotency
    conn.executescript(SCHEMA_V3_MIGRATION)

    # Populate FTS5 index with existing posts
    # Pitfall #2: FTS5 table is empty after creation even with content='posts'
    conn.execute("""
        INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
        SELECT rowid, text, author_username, author_display_name FROM posts
    """)

    # Set schema version to 3
    conn.execute("PRAGMA user_version = 3")
    conn.commit()


def migrate_to_v4(conn: sqlite3.Connection) -> None:
    """Migrate from v3 to v4: Add tags, topics, and embeddings tables.

    Idempotent: Safe to call multiple times. Checks PRAGMA user_version
    before applying changes.

    ORG-01: Tags table for user-defined post tags.
    ORG-02: Topics table for predefined topic taxonomy.
    ORG-03: Post embeddings cache for clustering.
    ORG-04: Pending topic assignments for AI suggestions.

    Args:
        conn: SQLite connection.
    """
    current_version = get_schema_version_int(conn)

    # Idempotent: Skip if already at v4 or higher
    if current_version >= 4:
        return

    # Create tags, topics, and embeddings tables
    # This uses IF NOT EXISTS for idempotency
    conn.executescript(SCHEMA_V4_MIGRATION)

    # Set schema version to 4
    conn.execute("PRAGMA user_version = 4")
    conn.commit()


def migrate_to_v5(conn: sqlite3.Connection) -> None:
    """Migrate from v4 to v5: Add post_review_state table.

    Idempotent: Safe to call multiple times. Checks PRAGMA user_version
    before applying changes.

    SPAC-01: Review state table for spaced repetition scheduling.
    SPAC-02: scheduled_for column for due posts query.
    SPAC-04: post_id index for themed reviews join.

    Args:
        conn: SQLite connection.
    """
    current_version = get_schema_version_int(conn)

    # Idempotent: Skip if already at v5 or higher
    if current_version >= 5:
        return

    # Create post_review_state table
    # This uses IF NOT EXISTS for idempotency
    conn.executescript(SCHEMA_V5_MIGRATION)

    # Set schema version to 5
    conn.execute("PRAGMA user_version = 5")
    conn.commit()


def migrate_to_v6(conn: sqlite3.Connection) -> None:
    """Migrate from v5 to v6: Add embedded_posts table and post columns.

    Idempotent: Safe to call multiple times. Checks PRAGMA user_version
    before applying changes.

    STR-01: Embedded posts table stores original tweet content for retweets/quotes.
    STR-02: Posts table gains post_type and embedded_post_id columns.

    Args:
        conn: SQLite connection.
    """
    current_version = get_schema_version_int(conn)

    # Idempotent: Skip if already at v6 or higher
    if current_version >= 6:
        return

    # Create embedded_posts table
    # This uses IF NOT EXISTS for idempotency
    conn.executescript(SCHEMA_V6_MIGRATION)

    # Add post_type column (D-02)
    # SQLite doesn't support ALTER TABLE IF NOT EXISTS, so use try/except
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT 'original'")
    except sqlite3.OperationalError:
        # Column already exists, which is fine for idempotency
        pass

    # Add embedded_post_id column (D-02)
    try:
        conn.execute("ALTER TABLE posts ADD COLUMN embedded_post_id TEXT")
    except sqlite3.OperationalError:
        # Column already exists, which is fine for idempotency
        pass

    # Set schema version to 6
    conn.execute("PRAGMA user_version = 6")
    conn.commit()


def run_migrations(conn: sqlite3.Connection) -> int:
    """Run all pending database migrations.

    Applies migrations incrementally based on current PRAGMA user_version.
    Returns the final schema version.

    Args:
        conn: SQLite connection.

    Returns:
        Final schema version after all migrations.
    """
    current_version = get_schema_version_int(conn)

    # Run migrations in order
    # Note: v1 and v2 schemas are applied via init_database() using executescript
    # This function handles incremental migrations

    if current_version < 3:
        migrate_to_v3(conn)

    if current_version < 4:
        migrate_to_v4(conn)

    if current_version < 5:
        migrate_to_v5(conn)

    if current_version < 6:
        migrate_to_v6(conn)

    return get_schema_version_int(conn)


__all__ = ["get_schema_version_int", "migrate_to_v3", "migrate_to_v4", "migrate_to_v5", "migrate_to_v6", "run_migrations"]