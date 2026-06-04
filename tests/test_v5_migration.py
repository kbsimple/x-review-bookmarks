"""Tests for database schema V5 migration.

Tests for:
- Schema version tracking (PRAGMA user_version)
- Migration from v4 to v5 (post_review_state table)
- Migration idempotency
"""

import pytest
import sqlite3
from pathlib import Path
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSchemaV5Definition:
    """Tests for SCHEMA_V5_MIGRATION definition in schema.py."""

    def test_schema_v5_constant_exists(self):
        """Verify SCHEMA_V5_MIGRATION constant exists in schema module."""
        from src.db.schema import SCHEMA_V5_MIGRATION

        assert SCHEMA_V5_MIGRATION is not None
        assert len(SCHEMA_V5_MIGRATION) > 0

    def test_schema_v5_includes_post_review_state_table(self):
        """Verify SCHEMA_V5_MIGRATION includes post_review_state table.

        SPAC-01: Review state table for spaced repetition scheduling.
        """
        from src.db.schema import SCHEMA_V5_MIGRATION

        assert "post_review_state" in SCHEMA_V5_MIGRATION

    def test_schema_v5_includes_scheduled_for_column(self):
        """Verify SCHEMA_V5_MIGRATION includes scheduled_for column.

        SPAC-02: get_due_posts query returns posts where scheduled_for <= NOW.
        """
        from src.db.schema import SCHEMA_V5_MIGRATION

        assert "scheduled_for" in SCHEMA_V5_MIGRATION

    def test_schema_v5_includes_fsrs_columns(self):
        """Verify SCHEMA_V5_MIGRATION includes FSRS algorithm columns.

        FSRS columns: stability, difficulty, state, step, fsrs_data.
        """
        from src.db.schema import SCHEMA_V5_MIGRATION

        assert "stability" in SCHEMA_V5_MIGRATION
        assert "difficulty" in SCHEMA_V5_MIGRATION
        assert "state" in SCHEMA_V5_MIGRATION

    def test_schema_v5_includes_foreign_key_to_posts(self):
        """Verify SCHEMA_V5_MIGRATION includes foreign key to posts table."""
        from src.db.schema import SCHEMA_V5_MIGRATION

        # Should reference posts table with cascade delete
        assert "FOREIGN KEY" in SCHEMA_V5_MIGRATION.upper()
        assert "posts" in SCHEMA_V5_MIGRATION
        assert "ON DELETE CASCADE" in SCHEMA_V5_MIGRATION.upper()

    def test_schema_v5_includes_indexes(self):
        """Verify SCHEMA_V5_MIGRATION includes indexes for due posts query."""
        from src.db.schema import SCHEMA_V5_MIGRATION

        # Index on scheduled_for for due posts query
        assert "idx_review_state_scheduled" in SCHEMA_V5_MIGRATION
        # Index on post_id for themed reviews join
        assert "idx_review_state_post" in SCHEMA_V5_MIGRATION

    def test_get_schema_version_returns_v6(self):
        """Verify get_schema_version returns 'v6' after Phase 8."""
        from src.db.schema import get_schema_version

        assert get_schema_version() == "v6"


class TestV5Migration:
    """Tests for v5 schema migration: post_review_state table."""

    @pytest.fixture
    def temp_db_v4(self):
        """Create a temporary database with v4 schema applied."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Apply PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")

        # Apply v1 and v2 schemas
        from src.db.schema import SCHEMA_V1, SCHEMA_V2
        conn.executescript(SCHEMA_V1)
        conn.executescript(SCHEMA_V2)
        conn.commit()

        # Run v3 and v4 migrations
        from src.db.migrations import migrate_to_v3, migrate_to_v4
        migrate_to_v3(conn)
        migrate_to_v4(conn)

        yield conn

        conn.close()
        db_path.unlink(missing_ok=True)

    def test_migrate_to_v5_function_exists(self):
        """Verify migrate_to_v5 function exists in migrations module."""
        from src.db.migrations import migrate_to_v5

        assert callable(migrate_to_v5)

    def test_migrate_to_v5_creates_post_review_state_table(self, temp_db_v4):
        """Verify migrate_to_v5 creates post_review_state table.

        Test 1: migrate_to_v5 creates post_review_state table on fresh database.
        """
        from src.db.migrations import migrate_to_v5

        migrate_to_v5(temp_db_v4)

        result = temp_db_v4.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='post_review_state'"
        ).fetchone()

        assert result is not None

    def test_migrate_to_v5_idempotent(self, temp_db_v4):
        """Verify migrate_to_v5 is idempotent (safe to call multiple times).

        Test 2: migrate_to_v5 is idempotent (calling twice does not error).
        """
        from src.db.migrations import migrate_to_v5, get_schema_version_int

        migrate_to_v5(temp_db_v4)
        version_after_first = get_schema_version_int(temp_db_v4)
        assert version_after_first == 5

        # Run migration again (should skip)
        migrate_to_v5(temp_db_v4)
        version_after_second = get_schema_version_int(temp_db_v4)
        assert version_after_second == 5

    def test_migrate_to_v5_sets_pragma_user_version(self, temp_db_v4):
        """Verify migrate_to_v5 sets PRAGMA user_version = 5."""
        from src.db.migrations import migrate_to_v5, get_schema_version_int

        migrate_to_v5(temp_db_v4)

        version = get_schema_version_int(temp_db_v4)
        assert version == 5

    def test_get_schema_version_returns_v6_after_migration(self, temp_db_v4):
        """Verify get_schema_version returns 'v6' after all migrations.

        Test 3: get_schema_version returns "v6" after all migrations including v6.
        """
        from src.db.schema import get_schema_version

        # This checks the constant, not the database version
        assert get_schema_version() == "v6"

    def test_run_migrations_applies_v5(self, temp_db_v4):
        """Verify run_migrations applies v5 migration."""
        from src.db.migrations import run_migrations, get_schema_version_int

        # Reset version to 4 to test that run_migrations applies v5
        temp_db_v4.execute("PRAGMA user_version = 4")
        temp_db_v4.commit()

        final_version = run_migrations(temp_db_v4)

        assert final_version >= 5
        assert get_schema_version_int(temp_db_v4) == final_version


class TestSchemaV5Integration:
    """Integration tests for v5 schema components."""

    @pytest.fixture
    def temp_db_v5(self):
        """Create a temporary database with v5 schema applied."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Apply PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")

        # Apply v1 and v2 schemas
        from src.db.schema import SCHEMA_V1, SCHEMA_V2
        conn.executescript(SCHEMA_V1)
        conn.executescript(SCHEMA_V2)
        conn.commit()

        # Run all migrations
        from src.db.migrations import run_migrations
        run_migrations(conn)

        yield conn

        conn.close()
        db_path.unlink(missing_ok=True)

    def test_post_review_state_table_columns(self, temp_db_v5):
        """Verify post_review_state table has all required columns."""
        columns = temp_db_v5.execute("PRAGMA table_info(post_review_state)").fetchall()
        column_names = [col[1] for col in columns]

        # Required columns per plan
        required_columns = [
            "post_id",
            "scheduled_for",
            "last_reviewed",
            "review_count",
            "user_preference",
            "stability",
            "difficulty",
            "state",
            "step",
            "fsrs_data",
            "created_at",
            "updated_at",
        ]

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_post_review_state_foreign_key_cascade(self, temp_db_v5):
        """Verify foreign key cascade deletes review state when post is deleted."""
        # Insert a post
        temp_db_v5.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("test_post_fk", "2024-01-01T00:00:00Z", "Test post", "user_1", "testuser"))
        temp_db_v5.commit()

        # Insert review state
        temp_db_v5.execute("""
            INSERT INTO post_review_state (
                post_id, scheduled_for
            ) VALUES (?, ?)
        """, ("test_post_fk", "2024-01-15T00:00:00Z"))
        temp_db_v5.commit()

        # Verify review state exists
        count_before = temp_db_v5.execute(
            "SELECT COUNT(*) FROM post_review_state WHERE post_id = ?",
            ("test_post_fk",)
        ).fetchone()[0]
        assert count_before == 1

        # Delete the post
        temp_db_v5.execute("DELETE FROM posts WHERE x_post_id = ?", ("test_post_fk",))
        temp_db_v5.commit()

        # Verify review state was cascade deleted
        count_after = temp_db_v5.execute(
            "SELECT COUNT(*) FROM post_review_state WHERE post_id = ?",
            ("test_post_fk",)
        ).fetchone()[0]
        assert count_after == 0

    def test_scheduled_for_index_exists(self, temp_db_v5):
        """Verify idx_review_state_scheduled index exists."""
        indexes = temp_db_v5.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_review_state_scheduled'"
        ).fetchone()

        assert indexes is not None

    def test_post_id_index_exists(self, temp_db_v5):
        """Verify idx_review_state_post index exists."""
        indexes = temp_db_v5.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_review_state_post'"
        ).fetchone()

        assert indexes is not None

    def test_post_review_state_defaults(self, temp_db_v5):
        """Verify default values for post_review_state columns."""
        # Insert a post first
        temp_db_v5.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("test_defaults", "2024-01-01T00:00:00Z", "Test post", "user_1", "testuser"))
        temp_db_v5.commit()

        # Insert review state with minimal fields
        temp_db_v5.execute("""
            INSERT INTO post_review_state (
                post_id, scheduled_for
            ) VALUES (?, ?)
        """, ("test_defaults", "2024-01-15T00:00:00Z"))
        temp_db_v5.commit()

        # Retrieve and check defaults
        row = temp_db_v5.execute(
            "SELECT * FROM post_review_state WHERE post_id = ?",
            ("test_defaults",)
        ).fetchone()

        assert row["review_count"] == 0
        assert row["state"] == 0  # FSRS state: new