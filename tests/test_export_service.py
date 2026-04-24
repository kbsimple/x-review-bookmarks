"""Tests for ExportService.

Tests for:
- Export posts to JSON with metadata wrapper (IMEX-01)
- Export posts to CSV with core fields (IMEX-02)
- Import posts from JSON export (IMEX-03)

Wave 0 scaffold - tests will be implemented in Wave 2.
"""

import pytest
import sqlite3
from pathlib import Path
import sys
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_with_posts():
    """Create a temporary database with test posts for export/import.

    Yields:
        sqlite3.Connection: Connection with sample posts.
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

    # Create posts table with v3 schema
    conn.execute("""
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

    conn.commit()

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_export_file():
    """Create a temporary file path for export/import tests.

    Yields:
        Path: Path to temporary export file.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        export_path = Path(f.name)

    yield export_path

    export_path.unlink(missing_ok=True)


class TestExportService:
    """Tests for ExportService JSON and CSV export/import.

    IMEX-01: Export posts to JSON with metadata wrapper.
    IMEX-02: Export posts to CSV with core fields.
    IMEX-03: Import posts from JSON export.
    """

    def test_export_to_json_with_metadata(self, temp_db_with_posts, temp_export_file):
        """Verify JSON export includes metadata wrapper.

        IMEX-01: JSON format with version, exported_at, source, post_count.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_export_to_json_includes_all_posts(self, temp_db_with_posts, temp_export_file):
        """Verify JSON export includes all posts from database.

        IMEX-01: All posts exported to JSON.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_export_to_csv_core_fields(self, temp_db_with_posts, temp_export_file):
        """Verify CSV export includes core fields only.

        IMEX-02: CSV with x_post_id, text, author_username, created_at, note.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_export_to_csv_excludes_arrays(self, temp_db_with_posts, temp_export_file):
        """Verify CSV export excludes media_urls and link_urls arrays.

        IMEX-02: Media/link arrays omitted from CSV.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_import_from_json_validates_version(self, temp_db_with_posts):
        """Verify JSON import validates version field.

        IMEX-03: Import validates JSON version before processing.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_import_from_json_skip_existing(self, temp_db_with_posts):
        """Verify JSON import skips existing posts by default.

        IMEX-03: Import with conflict='skip' (default).

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_import_from_json_update_existing(self, temp_db_with_posts):
        """Verify JSON import updates existing posts when requested.

        IMEX-03: Import with conflict='update'.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_import_from_json_validates_source(self, temp_db_with_posts):
        """Verify JSON import validates source field.

        IMEX-03: Import validates source='xbm' before processing.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")

    def test_import_handles_missing_optional_fields(self, temp_db_with_posts):
        """Verify JSON import handles missing optional fields gracefully.

        Edge case: Import JSON with missing note, media_urls, link_urls.

        Implemented in Wave 2.
        """
        pytest.skip("Implemented in Wave 2")