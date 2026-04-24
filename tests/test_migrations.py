"""Tests for database migrations.

Tests for:
- Schema version tracking (PRAGMA user_version)
- Migration from v2 to v3 (FTS5, note, link_status)
- Migration idempotency
"""

import pytest
import sqlite3
from pathlib import Path
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSchemaV3Definition:
    """Tests for SCHEMA_V3_MIGRATION definition in schema.py."""

    def test_schema_v3_constant_exists(self):
        """Verify SCHEMA_V3_MIGRATION constant exists in schema module."""
        from src.db.schema import SCHEMA_V3_MIGRATION

        assert SCHEMA_V3_MIGRATION is not None
        assert len(SCHEMA_V3_MIGRATION) > 0

    def test_schema_v3_includes_note_column_comment(self):
        """Verify SCHEMA_V3_MIGRATION includes note column reference.

        NOTE-01: User can add personal notes to bookmarked posts.
        Note: ALTER TABLE handled in migrations.py, not in schema constant.
        """
        from src.db.schema import SCHEMA_V3_MIGRATION

        # The migration constant documents the note column
        assert "note" in SCHEMA_V3_MIGRATION.lower()

    def test_schema_v3_includes_link_status_column_comment(self):
        """Verify SCHEMA_V3_MIGRATION includes link_status column reference.

        MAINT-01: Application detects and flags dead links.
        Note: ALTER TABLE handled in migrations.py, not in schema constant.
        """
        from src.db.schema import SCHEMA_V3_MIGRATION

        # The migration constant documents the link_status column
        assert "link_status" in SCHEMA_V3_MIGRATION.lower()

    def test_schema_v3_includes_fts5_virtual_table(self):
        """Verify SCHEMA_V3_MIGRATION includes FTS5 virtual table definition.

        SRCH-01: Full-text search within stored post content.
        """
        from src.db.schema import SCHEMA_V3_MIGRATION

        # Should include FTS5 virtual table
        assert "posts_fts" in SCHEMA_V3_MIGRATION
        assert "fts5" in SCHEMA_V3_MIGRATION.lower()

    def test_schema_v3_includes_insert_trigger(self):
        """Verify SCHEMA_V3_MIGRATION includes INSERT trigger for FTS5 sync.

        Critical: FTS5 index must stay synchronized with posts table.
        """
        from src.db.schema import SCHEMA_V3_MIGRATION

        # Should include INSERT trigger
        assert "posts_ai" in SCHEMA_V3_MIGRATION
        assert "AFTER INSERT" in SCHEMA_V3_MIGRATION

    def test_schema_v3_includes_delete_trigger(self):
        """Verify SCHEMA_V3_MIGRATION includes DELETE trigger for FTS5 sync."""
        from src.db.schema import SCHEMA_V3_MIGRATION

        # Should include DELETE trigger
        assert "posts_ad" in SCHEMA_V3_MIGRATION
        assert "AFTER DELETE" in SCHEMA_V3_MIGRATION

    def test_schema_v3_includes_update_trigger(self):
        """Verify SCHEMA_V3_MIGRATION includes UPDATE trigger for FTS5 sync."""
        from src.db.schema import SCHEMA_V3_MIGRATION

        # Should include UPDATE trigger
        assert "posts_au" in SCHEMA_V3_MIGRATION
        assert "AFTER UPDATE" in SCHEMA_V3_MIGRATION

    def test_get_schema_version_returns_v3(self):
        """Verify get_schema_version returns 'v3' after Phase 3."""
        from src.db.schema import get_schema_version

        assert get_schema_version() == "v3"


class TestMigrationsModule:
    """Tests for migrations.py module."""

    @pytest.fixture
    def temp_db_v2(self):
        """Create a temporary database with v2 schema (no note, link_status, FTS5)."""
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

        yield conn

        conn.close()
        db_path.unlink(missing_ok=True)

    def test_migrate_to_v3_function_exists(self):
        """Verify migrate_to_v3 function exists in migrations module."""
        from src.db.migrations import migrate_to_v3

        assert callable(migrate_to_v3)

    def test_migrate_to_v3_checks_pragma_user_version(self, temp_db_v2):
        """Verify migrate_to_v3 checks PRAGMA user_version before applying."""
        from src.db.migrations import migrate_to_v3, get_schema_version_int

        # v2 database should have user_version = 0 (not set) or 2
        version_before = get_schema_version_int(temp_db_v2)
        assert version_before < 3

        # Run migration
        migrate_to_v3(temp_db_v2)

        # Should now be v3
        version_after = get_schema_version_int(temp_db_v2)
        assert version_after == 3

    def test_migrate_to_v3_skips_if_already_v3(self, temp_db_v2):
        """Verify migrate_to_v3 is idempotent (safe to call multiple times)."""
        from src.db.migrations import migrate_to_v3, get_schema_version_int

        # Run migration once
        migrate_to_v3(temp_db_v2)
        version_after_first = get_schema_version_int(temp_db_v2)
        assert version_after_first == 3

        # Run migration again (should skip)
        migrate_to_v3(temp_db_v2)
        version_after_second = get_schema_version_int(temp_db_v2)
        assert version_after_second == 3

    def test_migrate_to_v3_populates_fts5_index(self, temp_db_v2):
        """Verify migrate_to_v3 populates FTS5 index from existing posts."""
        from src.db.migrations import migrate_to_v3

        # Insert a test post before migration
        temp_db_v2.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("test_post_1", "2024-01-01T00:00:00Z", "Test post content", "user_1", "testuser"))
        temp_db_v2.commit()

        # Run migration
        migrate_to_v3(temp_db_v2)

        # Check FTS5 index has the post
        result = temp_db_v2.execute(
            "SELECT COUNT(*) FROM posts_fts WHERE posts_fts MATCH 'Test'"
        ).fetchone()
        assert result[0] == 1, "FTS5 index should contain existing post"

    def test_migrate_to_v3_sets_pragma_user_version(self, temp_db_v2):
        """Verify migrate_to_v3 sets PRAGMA user_version = 3 after migration."""
        from src.db.migrations import migrate_to_v3, get_schema_version_int

        migrate_to_v3(temp_db_v2)

        version = get_schema_version_int(temp_db_v2)
        assert version == 3

    def test_get_schema_version_int_returns_integer(self, temp_db_v2):
        """Verify get_schema_version_int returns integer version number."""
        from src.db.migrations import get_schema_version_int

        version = get_schema_version_int(temp_db_v2)

        assert isinstance(version, int)
        assert version >= 0

    def test_run_migrations_function_exists(self):
        """Verify run_migrations function exists in migrations module."""
        from src.db.migrations import run_migrations

        assert callable(run_migrations)

    def test_run_migrations_applies_pending_migrations(self, temp_db_v2):
        """Verify run_migrations applies all pending migrations."""
        from src.db.migrations import run_migrations, get_schema_version_int

        final_version = run_migrations(temp_db_v2)

        assert final_version >= 3
        assert get_schema_version_int(temp_db_v2) == final_version


class TestSchemaV3Integration:
    """Integration tests for v3 schema components."""

    @pytest.fixture
    def temp_db_v3(self):
        """Create a temporary database with v3 schema applied."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Apply PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")

        # Apply all schemas
        from src.db.schema import SCHEMA_V1, SCHEMA_V2
        conn.executescript(SCHEMA_V1)
        conn.executescript(SCHEMA_V2)
        conn.commit()

        # Run migrations
        from src.db.migrations import run_migrations
        run_migrations(conn)

        yield conn

        conn.close()
        db_path.unlink(missing_ok=True)

    def test_posts_table_has_note_column_after_migration(self, temp_db_v3):
        """Verify posts table has note column after v3 migration."""
        columns = temp_db_v3.execute("PRAGMA table_info(posts)").fetchall()
        column_names = [col[1] for col in columns]

        assert "note" in column_names

    def test_posts_table_has_link_status_column_after_migration(self, temp_db_v3):
        """Verify posts table has link_status column after v3 migration."""
        columns = temp_db_v3.execute("PRAGMA table_info(posts)").fetchall()
        column_names = [col[1] for col in columns]

        assert "link_status" in column_names

    def test_fts5_virtual_table_exists_after_migration(self, temp_db_v3):
        """Verify posts_fts virtual table exists after v3 migration."""
        result = temp_db_v3.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts_fts'"
        ).fetchone()

        assert result is not None

    def test_fts5_triggers_exist_after_migration(self, temp_db_v3):
        """Verify FTS5 sync triggers exist after v3 migration."""
        triggers = temp_db_v3.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'posts_%'"
        ).fetchall()
        trigger_names = [t[0] for t in triggers]

        assert "posts_ai" in trigger_names
        assert "posts_ad" in trigger_names
        assert "posts_au" in trigger_names

    def test_fts5_search_returns_results(self, temp_db_v3):
        """Verify FTS5 search returns matching posts."""
        # Insert test post
        temp_db_v3.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("test_search_1", "2024-01-01T00:00:00Z", "This is a test post about Python", "user_1", "pythonista"))
        temp_db_v3.commit()

        # Search for "Python"
        results = temp_db_v3.execute(
            "SELECT * FROM posts_fts WHERE posts_fts MATCH ?",
            ("Python",)
        ).fetchall()

        assert len(results) == 1

    def test_fts5_sync_on_insert(self, temp_db_v3):
        """Verify FTS5 index updates when post is inserted."""
        # Insert a post
        temp_db_v3.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("trigger_test_1", "2024-01-01T00:00:00Z", "Trigger test content", "user_1", "testuser"))
        temp_db_v3.commit()

        # Verify FTS5 index was updated via trigger
        count = temp_db_v3.execute("SELECT COUNT(*) FROM posts_fts").fetchone()[0]
        assert count == 1

    def test_fts5_sync_on_update(self, temp_db_v3):
        """Verify FTS5 index updates when post text is updated."""
        # Insert a post
        temp_db_v3.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("update_test_1", "2024-01-01T00:00:00Z", "Original text", "user_1", "testuser"))
        temp_db_v3.commit()

        # Update the post
        temp_db_v3.execute("""
            UPDATE posts SET text = ? WHERE x_post_id = ?
        """, ("Updated text with newword", "update_test_1"))
        temp_db_v3.commit()

        # Verify FTS5 index has the update
        results = temp_db_v3.execute(
            "SELECT * FROM posts_fts WHERE posts_fts MATCH ?",
            ("newword",)
        ).fetchall()

        assert len(results) == 1

    def test_fts5_sync_on_delete(self, temp_db_v3):
        """Verify FTS5 index removes entry when post is deleted."""
        # Insert a post
        temp_db_v3.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("delete_test_1", "2024-01-01T00:00:00Z", "Post to delete", "user_1", "testuser"))
        temp_db_v3.commit()

        # Verify it's in FTS5
        count_before = temp_db_v3.execute("SELECT COUNT(*) FROM posts_fts").fetchone()[0]
        assert count_before == 1

        # Delete the post
        temp_db_v3.execute("DELETE FROM posts WHERE x_post_id = ?", ("delete_test_1",))
        temp_db_v3.commit()

        # Verify FTS5 index was updated
        count_after = temp_db_v3.execute("SELECT COUNT(*) FROM posts_fts").fetchone()[0]
        assert count_after == 0

    def test_link_status_default_value(self, temp_db_v3):
        """Verify link_status has default value 'unchecked'."""
        # Insert a post without link_status
        temp_db_v3.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username
            ) VALUES (?, ?, ?, ?, ?)
        """, ("default_test_1", "2024-01-01T00:00:00Z", "Test post", "user_1", "testuser"))
        temp_db_v3.commit()

        # Retrieve and check default
        row = temp_db_v3.execute(
            "SELECT link_status FROM posts WHERE x_post_id = ?",
            ("default_test_1",)
        ).fetchone()

        assert row["link_status"] == "unchecked"