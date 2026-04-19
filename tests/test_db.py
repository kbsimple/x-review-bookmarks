"""Tests for SQLite database module.

Tests STOR-01: Database with WAL mode enabled
Tests STOR-02: Foreign key constraints enforced
"""

import pytest
import sqlite3


class TestDatabaseInitialization:
    """Tests for STOR-01: SQLite with WAL mode."""

    def test_wal_mode_enabled(self, temp_db):
        """Verify WAL mode is enabled on database connection.

        STOR-01: Application stores posts in SQLite database with WAL mode enabled.

        Expected behavior:
        - PRAGMA journal_mode returns 'wal'
        - Connection factory applies WAL mode automatically
        """
        raise NotImplementedError("Implement after src/db/connection.py exists")

    def test_database_file_created(self):
        """Verify database file is created at correct location.

        Expected behavior:
        - Database file created at data/bookmarks.db (default)
        - data/ directory created if it doesn't exist
        """
        raise NotImplementedError("Implement after src/db/__init__.py exists")


class TestForeignKeys:
    """Tests for STOR-02: Foreign key constraints."""

    def test_foreign_keys_enabled(self, temp_db):
        """Verify foreign_keys pragma is ON.

        STOR-02: Application enables foreign key constraints.

        Expected behavior:
        - PRAGMA foreign_keys returns 1 (ON)
        - Connection factory enables foreign_keys automatically
        """
        raise NotImplementedError("Implement after src/db/connection.py exists")

    def test_foreign_key_enforcement(self, temp_db):
        """Verify foreign key constraints are actually enforced.

        STOR-02: FK constraints prevent orphaned records.

        Expected behavior:
        - INSERT into tokens table with non-existent user_id fails
        - SQLite raises FOREIGN KEY constraint failed error
        """
        raise NotImplementedError("Implement after src/db/schema.py exists")


class TestSchema:
    """Tests for database schema creation."""

    def test_users_table_created(self, temp_db):
        """Verify users table exists after initialization.

        Expected behavior:
        - users table created with: id, x_user_id, username, display_name, created_at
        - x_user_id has UNIQUE constraint
        """
        raise NotImplementedError("Implement after src/db/schema.py exists")

    def test_tokens_table_created(self, temp_db):
        """Verify tokens table exists after initialization.

        Expected behavior:
        - tokens table created with: id, user_id, access_token, refresh_token, expires_at, created_at, updated_at
        - user_id has FOREIGN KEY to users.id
        - Index idx_tokens_user_id created
        """
        raise NotImplementedError("Implement after src/db/schema.py exists")

    def test_schema_v1_applied(self, temp_db):
        """Verify SCHEMA_V1 creates all required tables.

        Expected behavior:
        - users and tokens tables created
        - Index created on tokens.user_id
        - No errors on schema application
        """
        raise NotImplementedError("Implement after src/db/schema.py exists")


class TestConnectionFactory:
    """Tests for connection factory function."""

    def test_connection_returns_valid_connection(self):
        """Verify get_connection returns usable SQLite connection.

        Expected behavior:
        - Connection is sqlite3.Connection instance
        - Connection can execute queries
        - Row factory set to sqlite3.Row
        """
        raise NotImplementedError("Implement after src/db/connection.py exists")

    def test_connection_applies_all_pragmas(self):
        """Verify connection factory applies all required PRAGMAs.

        Expected behavior:
        - foreign_keys = ON
        - journal_mode = WAL
        - synchronous = NORMAL
        - busy_timeout = 5000
        """
        raise NotImplementedError("Implement after src/db/connection.py exists")

    def test_connection_factory_idempotent(self):
        """Verify multiple calls to get_connection work correctly.

        Expected behavior:
        - Each call returns new connection
        - Each connection has PRAGMAs applied
        """
        raise NotImplementedError("Implement after src/db/connection.py exists")