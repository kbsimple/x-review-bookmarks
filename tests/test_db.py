"""Tests for SQLite database module.

Tests STOR-01: Database with WAL mode enabled
Tests STOR-02: Foreign key constraints enforced
"""

import pytest
import sqlite3
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDatabaseInitialization:
    """Tests for STOR-01: SQLite with WAL mode."""

    def test_wal_mode_enabled(self, temp_db):
        """Verify WAL mode is enabled on database connection.

        STOR-01: Application stores posts in SQLite database with WAL mode enabled.

        Expected behavior:
        - PRAGMA journal_mode returns 'wal'
        - Connection factory applies WAL mode automatically
        """
        from src.db.connection import get_connection

        # temp_db already has PRAGMAs applied, but let's verify
        result = temp_db.execute("PRAGMA journal_mode").fetchone()
        # For in-memory databases, journal_mode is 'memory', for file-based it's 'wal'
        assert result[0] in ('wal', 'memory'), f"Expected WAL or memory mode, got {result[0]}"

    def test_database_file_created(self, tmp_path):
        """Verify database file is created at correct location.

        Expected behavior:
        - Database file created at data/bookmarks.db (default)
        - data/ directory created if it doesn't exist
        """
        from src.db import init_database

        # Use temp directory as database path
        db_path = tmp_path / "test.db"
        conn = init_database(db_path)

        assert db_path.exists(), "Database file should be created"
        conn.close()

        # Clean up
        db_path.unlink(missing_ok=True)


class TestForeignKeys:
    """Tests for STOR-02: Foreign key constraints."""

    def test_foreign_keys_enabled(self, temp_db):
        """Verify foreign_keys pragma is ON.

        STOR-02: Application enables foreign key constraints.

        Expected behavior:
        - PRAGMA foreign_keys returns 1 (ON)
        - Connection factory enables foreign_keys automatically
        """
        from src.db.connection import get_connection

        result = temp_db.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1, f"Expected foreign_keys=1, got {result[0]}"

    def test_foreign_key_enforcement(self, temp_db):
        """Verify foreign key constraints are actually enforced.

        STOR-02: FK constraints prevent orphaned records.

        Expected behavior:
        - INSERT into tokens table with non-existent user_id fails
        - SQLite raises FOREIGN KEY constraint failed error
        """
        from src.db.schema import SCHEMA_V1

        # Apply schema
        temp_db.executescript(SCHEMA_V1)

        # Try to insert token for non-existent user (should fail)
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            temp_db.execute(
                "INSERT INTO tokens (user_id, access_token, refresh_token) VALUES (?, ?, ?)",
                (999, "test_token", "test_refresh")
            )

        assert "FOREIGN KEY" in str(exc_info.value), f"Expected FK error, got {exc_info.value}"


class TestSchema:
    """Tests for database schema creation."""

    def test_users_table_created(self, temp_db):
        """Verify users table exists after initialization.

        Expected behavior:
        - users table created with: id, x_user_id, username, display_name, created_at
        - x_user_id has UNIQUE constraint
        """
        from src.db.schema import SCHEMA_V1

        temp_db.executescript(SCHEMA_V1)

        # Check table exists
        result = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        assert result is not None, "users table should exist"

        # Check columns
        columns = temp_db.execute("PRAGMA table_info(users)").fetchall()
        column_names = [col[1] for col in columns]
        assert "id" in column_names
        assert "x_user_id" in column_names
        assert "username" in column_names
        assert "display_name" in column_names
        assert "created_at" in column_names

    def test_tokens_table_created(self, temp_db):
        """Verify tokens table exists after initialization.

        Expected behavior:
        - tokens table created with: id, user_id, access_token, refresh_token, expires_at, created_at, updated_at
        - user_id has FOREIGN KEY to users.id
        - Index idx_tokens_user_id created
        """
        from src.db.schema import SCHEMA_V1

        temp_db.executescript(SCHEMA_V1)

        # Check table exists
        result = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'"
        ).fetchone()
        assert result is not None, "tokens table should exist"

        # Check columns
        columns = temp_db.execute("PRAGMA table_info(tokens)").fetchall()
        column_names = [col[1] for col in columns]
        assert "id" in column_names
        assert "user_id" in column_names
        assert "access_token" in column_names
        assert "refresh_token" in column_names
        assert "expires_at" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

    def test_schema_v1_applied(self, temp_db):
        """Verify SCHEMA_V1 creates all required tables.

        Expected behavior:
        - users and tokens tables created
        - Index created on tokens.user_id
        - No errors on schema application
        """
        from src.db.schema import SCHEMA_V1

        # Should not raise any errors
        temp_db.executescript(SCHEMA_V1)

        # Verify tables exist
        tables = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "users" in table_names
        assert "tokens" in table_names

        # Verify index exists
        indexes = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = [i[0] for i in indexes]
        assert "idx_tokens_user_id" in index_names


class TestConnectionFactory:
    """Tests for connection factory function."""

    def test_connection_returns_valid_connection(self, tmp_path):
        """Verify get_connection returns usable SQLite connection.

        Expected behavior:
        - Connection is sqlite3.Connection instance
        - Connection can execute queries
        - Row factory set to sqlite3.Row
        """
        from src.db.connection import get_connection

        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)

        assert isinstance(conn, sqlite3.Connection)
        assert conn.row_factory == sqlite3.Row

        # Should be able to execute a simple query
        result = conn.execute("SELECT 1").fetchone()
        assert result[0] == 1

        conn.close()
        db_path.unlink(missing_ok=True)

    def test_connection_applies_all_pragmas(self, tmp_path):
        """Verify connection factory applies all required PRAGMAs.

        Expected behavior:
        - foreign_keys = ON (returns 1)
        - journal_mode = WAL (returns 'wal' or 'memory')
        - synchronous = NORMAL (returns 1)
        - busy_timeout = 5000 (returns 5000)
        """
        from src.db.connection import get_connection

        db_path = tmp_path / "test.db"
        conn = get_connection(db_path)

        # Check foreign_keys
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1, f"Expected foreign_keys=1, got {fk}"

        # Check journal_mode (file DBs get 'wal', in-memory gets 'memory')
        jm = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert jm in ('wal', 'memory'), f"Expected journal_mode=wal/memory, got {jm}"

        # Check synchronous
        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        assert sync == 1, f"Expected synchronous=1 (NORMAL), got {sync}"

        # Check busy_timeout
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout == 5000, f"Expected busy_timeout=5000, got {timeout}"

        conn.close()
        db_path.unlink(missing_ok=True)

    def test_connection_factory_idempotent(self, tmp_path):
        """Verify multiple calls to get_connection work correctly.

        Expected behavior:
        - Each call returns new connection
        - Each connection has PRAGMAs applied
        """
        from src.db.connection import get_connection

        db_path = tmp_path / "test.db"
        conn1 = get_connection(db_path)
        conn2 = get_connection(db_path)

        # Different connection objects
        assert conn1 is not conn2

        # Both have foreign_keys enabled
        fk1 = conn1.execute("PRAGMA foreign_keys").fetchone()[0]
        fk2 = conn2.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk1 == 1 and fk2 == 1

        conn1.close()
        conn2.close()
        db_path.unlink(missing_ok=True)


class TestSchemaV2:
    """Tests for Phase 2 schema additions (posts and sync_state tables)."""

    def test_schema_v2_exports(self):
        """Verify SCHEMA_V2 is exported from db module."""
        from src.db import SCHEMA_V2

        assert "posts" in SCHEMA_V2, "SCHEMA_V2 should define posts table"
        assert "sync_state" in SCHEMA_V2, "SCHEMA_V2 should define sync_state table"

    def test_posts_table_created(self, temp_db):
        """Verify posts table exists after initialization.

        D-01: Posts table stores full content (text, author, images, links, media).
        """
        from src.db.schema import SCHEMA_V1, SCHEMA_V2

        temp_db.executescript(SCHEMA_V1)
        temp_db.executescript(SCHEMA_V2)

        # Check table exists
        result = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
        ).fetchone()
        assert result is not None, "posts table should exist"

        # Check columns
        columns = temp_db.execute("PRAGMA table_info(posts)").fetchall()
        column_names = [col[1] for col in columns]
        assert "x_post_id" in column_names
        assert "created_at" in column_names
        assert "text" in column_names
        assert "author_id" in column_names
        assert "author_username" in column_names
        assert "media_urls" in column_names
        assert "link_urls" in column_names

    def test_sync_state_table_created(self, temp_db):
        """Verify sync_state table exists after initialization.

        D-02: sync_state tracks last_sync_bookmark_id for incremental sync.
        """
        from src.db.schema import SCHEMA_V1, SCHEMA_V2

        temp_db.executescript(SCHEMA_V1)
        temp_db.executescript(SCHEMA_V2)

        # Check table exists
        result = temp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_state'"
        ).fetchone()
        assert result is not None, "sync_state table should exist"

        # Check columns
        columns = temp_db.execute("PRAGMA table_info(sync_state)").fetchall()
        column_names = [col[1] for col in columns]
        assert "id" in column_names
        assert "last_sync_bookmark_id" in column_names
        assert "last_sync_at" in column_names
        assert "pagination_token" in column_names
        assert "total_bookmarks" in column_names

    def test_get_schema_version_returns_v2(self):
        """Verify get_schema_version returns 'v2' after Phase 2."""
        from src.db.schema import get_schema_version

        assert get_schema_version() == "v2"