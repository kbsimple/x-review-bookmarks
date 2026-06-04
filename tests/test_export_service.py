"""Tests for ExportService and ImportService.

Tests for:
- Export posts to JSON with metadata wrapper (IMEX-01)
- Export posts to CSV with core fields (IMEX-02)
- Import posts from JSON export (IMEX-03)

Wave 2 implementation for Phase 3, Plan 03.
"""

import csv
import json
import sqlite3
import sys
import tempfile
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

import pytest

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

    # Create posts table with v6 schema (includes post_type and embedded_post_id)
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
            link_status TEXT DEFAULT 'unchecked',
            post_type TEXT DEFAULT 'original',
            embedded_post_id TEXT
        )
    """)

    conn.commit()

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_export_dir(tmp_path):
    """Create a temporary directory for export files.

    Yields:
        Path: Path to temporary export directory.
    """
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    yield export_dir


@pytest.fixture
def sample_posts(temp_db_with_posts):
    """Insert sample posts into the database.

    Returns:
        list[dict]: List of inserted posts as dicts.
    """
    from src.repositories.posts import PostsRepository

    repo = PostsRepository(temp_db_with_posts)

    posts = [
        {
            "x_post_id": "post_001",
            "created_at": "2024-01-15T10:30:00Z",
            "text": "First post with some content",
            "author_id": "user_123",
            "author_username": "testuser1",
            "author_display_name": "Test User One",
            "media_urls": ["https://example.com/image1.jpg"],
            "link_urls": ["https://example.com/article1"],
            "note": "My note on first post",
        },
        {
            "x_post_id": "post_002",
            "created_at": "2024-01-16T14:20:00Z",
            "text": "Second post about Python programming",
            "author_id": "user_456",
            "author_username": "pythonista",
            "author_display_name": "Python Developer",
            "media_urls": [],
            "link_urls": [],
            "note": None,
        },
        {
            "x_post_id": "post_003",
            "created_at": "2024-01-17T09:00:00Z",
            "text": "Third post with Unicode: \u4e2d\u6587\u65e5\u672c\u8a9e",
            "author_id": "user_789",
            "author_username": "unicode_user",
            "author_display_name": "Unicode Tester",
            "media_urls": ["https://example.com/image2.jpg", "https://example.com/image3.jpg"],
            "link_urls": ["https://example.com/link1", "https://example.com/link2"],
            "note": "Unicode test note",
        },
    ]

    for post in posts:
        repo.insert_post(post)

    # Return posts with the note field included
    return [repo.get_by_id(post["x_post_id"]) for post in posts]


class TestExportService:
    """Tests for ExportService JSON and CSV export.

    IMEX-01: Export posts to JSON with metadata wrapper.
    IMEX-02: Export posts to CSV with core fields.
    """

    def test_export_service_init_accepts_repository(self, temp_db_with_posts):
        """Verify ExportService.__init__() accepts PostsRepository."""
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        assert service is not None
        assert hasattr(service, '_repo')
        assert service._repo is repo

    def test_export_json_creates_file_at_path(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() creates file at specified path.

        IMEX-01: User can export stored posts to JSON format.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        result = service.export_json(output_path)

        assert output_path.exists()
        assert result.path == output_path

    def test_export_json_includes_version(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() includes version: "1.0" in output.

        IMEX-01: JSON format includes version field.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        service.export_json(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data.get("version") == "1.0"

    def test_export_json_includes_exported_at_timestamp(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() includes exported_at timestamp in ISO format.

        IMEX-01: JSON format includes exported_at field.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        service.export_json(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "exported_at" in data
        # Should be ISO format
        exported_at = data["exported_at"]
        assert "T" in exported_at  # ISO format includes T separator

    def test_export_json_includes_source(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() includes source: "xbm" in output.

        IMEX-01: JSON format includes source field.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        service.export_json(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data.get("source") == "xbm"

    def test_export_json_includes_post_count(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() includes post_count matching posts array length.

        IMEX-01: JSON format includes post_count field.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        service.export_json(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "post_count" in data
        assert data["post_count"] == len(data["posts"])
        assert data["post_count"] == 3  # sample_posts has 3 posts

    def test_export_json_utf8_encoding(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() writes UTF-8 encoded JSON for Unicode content.

        IMEX-01: UTF-8 encoding for international content.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        service.export_json(output_path)

        # Read as UTF-8 and verify Unicode content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # The third post has Unicode content
        assert "\u4e2d\u6587\u65e5\u672c\u8a9e" in content

    def test_export_json_returns_result_with_count_and_path(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() returns ExportResult with count and path.

        IMEX-01: Export returns result object with metadata.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService, ExportResult

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        result = service.export_json(output_path)

        assert isinstance(result, ExportResult)
        assert result.post_count == 3
        assert result.path == output_path
        assert result.exported_at is not None

    def test_export_json_includes_all_post_fields(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_json() includes all post fields in posts array.

        IMEX-01: All post data exported to JSON.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.json"
        service.export_json(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data["posts"]) == 3

        # Check first post has all expected fields
        first_post = data["posts"][0]
        assert "x_post_id" in first_post
        assert "text" in first_post
        assert "author_username" in first_post
        assert "author_display_name" in first_post
        assert "created_at" in first_post
        assert "media_urls" in first_post
        assert "link_urls" in first_post
        assert "note" in first_post

    def test_export_csv_creates_file_with_core_fields(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_csv() creates CSV file with core fields.

        IMEX-02: CSV format includes core fields only.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.csv"
        result = service.export_csv(output_path)

        assert output_path.exists()
        assert result.path == output_path

        with open(output_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        assert "x_post_id" in fieldnames
        assert "text" in fieldnames
        assert "author_username" in fieldnames
        assert "author_display_name" in fieldnames
        assert "created_at" in fieldnames
        assert "note" in fieldnames

    def test_export_csv_omits_arrays(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_csv() omits media_urls and link_urls arrays.

        IMEX-02: Media/link arrays omitted from CSV.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.csv"
        service.export_csv(output_path)

        with open(output_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

        assert "media_urls" not in fieldnames
        assert "link_urls" not in fieldnames

    def test_export_csv_handles_null_note_as_empty_string(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_csv() converts NULL note to empty string.

        IMEX-02: NULL values become empty strings in CSV.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.csv"
        service.export_csv(output_path)

        with open(output_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Second post has NULL note
        second_post = [r for r in rows if r["x_post_id"] == "post_002"][0]
        assert second_post["note"] == ""

    def test_export_csv_returns_result_with_count(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify export_csv() returns ExportResult with count.

        IMEX-02: CSV export returns result object.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService, ExportResult

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "export.csv"
        result = service.export_csv(output_path)

        assert isinstance(result, ExportResult)
        assert result.post_count == 3

    def test_export_json_creates_parent_directories(self, temp_db_with_posts, sample_posts):
        """Verify export_json() creates parent directories if they don't exist.

        IMEX-01: Export handles missing directories.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        # Create path with non-existent parent directories
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "export.json"
            result = service.export_json(output_path)

            assert output_path.exists()
            assert output_path.parent.exists()

    def test_export_empty_database_produces_valid_json(self, temp_db_with_posts, temp_export_dir):
        """Verify export_json() handles empty database gracefully.

        Edge case: Export with no posts produces valid empty JSON.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService

        repo = PostsRepository(temp_db_with_posts)
        service = ExportService(repo)

        output_path = temp_export_dir / "empty_export.json"
        result = service.export_json(output_path)

        assert result.post_count == 0

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["posts"] == []
        assert data["post_count"] == 0


class TestImportService:
    """Tests for ImportService JSON import.

    IMEX-03: Import posts from JSON export.
    """

    def test_import_service_init_accepts_repository(self, temp_db_with_posts):
        """Verify ImportService.__init__() accepts PostsRepository."""
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        assert service is not None
        assert hasattr(service, '_repo')
        assert service._repo is repo

    def test_import_json_validates_version(self, temp_db_with_posts):
        """Verify import_json() validates version field equals "1.0".

        IMEX-03: Import validates JSON version.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create invalid version JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "version": "2.0",
                "source": "xbm",
                "posts": []
            }, f)
            invalid_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="version"):
                service.import_json(invalid_path)
        finally:
            invalid_path.unlink(missing_ok=True)

    def test_import_json_validates_source(self, temp_db_with_posts):
        """Verify import_json() validates source field equals "xbm".

        IMEX-03: Import validates source='xbm'.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create invalid source JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "version": "1.0",
                "source": "other",
                "posts": []
            }, f)
            invalid_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="source"):
                service.import_json(invalid_path)
        finally:
            invalid_path.unlink(missing_ok=True)

    def test_import_json_skips_existing_by_default(self, temp_db_with_posts, sample_posts):
        """Verify import_json() skips existing posts by default (conflict='skip').

        IMEX-03: Import with conflict='skip' (default).
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create JSON with existing post (post_001 already exists)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "version": "1.0",
                "exported_at": "2024-01-20T00:00:00Z",
                "source": "xbm",
                "post_count": 1,
                "posts": [{
                    "x_post_id": "post_001",
                    "text": "Updated text for existing post",
                    "author_id": "user_123",
                    "author_username": "testuser1",
                    "author_display_name": "Test User One",
                    "created_at": "2024-01-15T10:30:00Z",
                    "media_urls": [],
                    "link_urls": [],
                    "note": "Updated note"
                }]
            }, f)
            import_path = Path(f.name)

        try:
            result = service.import_json(import_path)  # Default conflict='skip'

            # Should skip existing post
            assert result.skipped_count == 1
            assert result.imported_count == 0

            # Verify original text unchanged
            post = repo.get_by_id("post_001")
            assert post["text"] == "First post with some content"
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_json_updates_existing_with_conflict_update(self, temp_db_with_posts, sample_posts):
        """Verify import_json() updates existing posts when conflict='update'.

        IMEX-03: Import with conflict='update'.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create JSON with updated post data
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "version": "1.0",
                "exported_at": "2024-01-20T00:00:00Z",
                "source": "xbm",
                "post_count": 1,
                "posts": [{
                    "x_post_id": "post_001",
                    "text": "Updated text for existing post",
                    "author_id": "user_123",
                    "author_username": "testuser1",
                    "author_display_name": "Test User One Updated",
                    "created_at": "2024-01-15T10:30:00Z",
                    "media_urls": [],
                    "link_urls": [],
                    "note": "Updated note"
                }]
            }, f)
            import_path = Path(f.name)

        try:
            result = service.import_json(import_path, conflict="update")

            # Should update existing post
            assert result.imported_count == 1
            assert result.skipped_count == 0

            # Verify updated text
            post = repo.get_by_id("post_001")
            assert post["text"] == "Updated text for existing post"
            assert post["note"] == "Updated note"
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_json_returns_result_with_counts(self, temp_db_with_posts, sample_posts):
        """Verify import_json() returns ImportResult with imported and skipped counts.

        IMEX-03: Import returns result object.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService, ImportResult

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create JSON with one new post and one existing
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "version": "1.0",
                "exported_at": "2024-01-20T00:00:00Z",
                "source": "xbm",
                "post_count": 2,
                "posts": [
                    {
                        "x_post_id": "post_001",  # Existing
                        "text": "Existing post",
                        "author_id": "user_123",
                        "author_username": "testuser1",
                        "created_at": "2024-01-15T10:30:00Z",
                        "media_urls": [],
                        "link_urls": [],
                        "note": None
                    },
                    {
                        "x_post_id": "new_post_999",  # New
                        "text": "Brand new post",
                        "author_id": "user_new",
                        "author_username": "newuser",
                        "created_at": "2024-01-20T10:00:00Z",
                        "media_urls": [],
                        "link_urls": [],
                        "note": "New note"
                    }
                ]
            }, f)
            import_path = Path(f.name)

        try:
            result = service.import_json(import_path)

            assert isinstance(result, ImportResult)
            assert result.imported_count == 1  # new_post_999
            assert result.skipped_count == 1   # post_001 (existing)
        finally:
            import_path.unlink(missing_ok=True)

    def test_import_json_handles_malformed_json(self, temp_db_with_posts):
        """Verify import_json() handles malformed JSON gracefully.

        Edge case: Invalid JSON raises JSONDecodeError.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create invalid JSON file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            f.write("{ invalid json content }")
            invalid_path = Path(f.name)

        try:
            with pytest.raises(json.JSONDecodeError):
                service.import_json(invalid_path)
        finally:
            invalid_path.unlink(missing_ok=True)

    def test_import_json_handles_missing_file(self, temp_db_with_posts):
        """Verify import_json() handles missing file gracefully.

        Edge case: Missing file raises FileNotFoundError.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        with pytest.raises(FileNotFoundError):
            service.import_json(Path("/nonexistent/path/file.json"))

    def test_import_json_handles_missing_optional_fields(self, temp_db_with_posts):
        """Verify import_json() handles missing optional fields gracefully.

        Edge case: Import JSON with missing note, media_urls, link_urls.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ImportService

        repo = PostsRepository(temp_db_with_posts)
        service = ImportService(repo)

        # Create JSON with minimal required fields only
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as f:
            json.dump({
                "version": "1.0",
                "exported_at": "2024-01-20T00:00:00Z",
                "source": "xbm",
                "post_count": 1,
                "posts": [{
                    "x_post_id": "minimal_post",
                    "text": "Minimal post",
                    "author_id": "user_min",
                    "author_username": "minimaluser",
                    "created_at": "2024-01-20T10:00:00Z"
                    # Missing: author_display_name, media_urls, link_urls, note
                }]
            }, f)
            import_path = Path(f.name)

        try:
            result = service.import_json(import_path)

            assert result.imported_count == 1

            # Verify post was imported with defaults for missing fields
            post = repo.get_by_id("minimal_post")
            assert post is not None
            assert post["text"] == "Minimal post"
        finally:
            import_path.unlink(missing_ok=True)


class TestRoundtrip:
    """Tests for export/import roundtrip integrity."""

    def test_roundtrip_export_import_preserves_data(self, temp_db_with_posts, temp_export_dir, sample_posts):
        """Verify roundtrip export/import preserves post data.

        End-to-end: Export to JSON, import to fresh DB, verify data matches.
        """
        from src.repositories.posts import PostsRepository
        from src.services.export import ExportService, ImportService

        repo = PostsRepository(temp_db_with_posts)

        # Export all posts to JSON
        export_service = ExportService(repo)
        export_path = temp_export_dir / "roundtrip.json"
        export_result = export_service.export_json(export_path)

        assert export_result.post_count == 3

        # Create new database for import
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            new_db_path = Path(f.name)

        new_conn = sqlite3.connect(str(new_db_path))
        new_conn.row_factory = sqlite3.Row
        new_conn.execute("PRAGMA foreign_keys = ON")
        new_conn.execute("PRAGMA journal_mode = WAL")

        # Create schema
        new_conn.execute("""
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
                link_status TEXT DEFAULT 'unchecked',
                post_type TEXT DEFAULT 'original',
                embedded_post_id TEXT
            )
        """)
        new_conn.commit()

        # Import into new database
        new_repo = PostsRepository(new_conn)
        import_service = ImportService(new_repo)
        import_result = import_service.import_json(export_path, conflict="update")

        assert import_result.imported_count == 3

        # Verify all posts match
        for original_post in sample_posts:
            imported_post = new_repo.get_by_id(original_post["x_post_id"])
            assert imported_post is not None
            assert imported_post["text"] == original_post["text"]
            assert imported_post["author_username"] == original_post["author_username"]
            assert imported_post["author_display_name"] == original_post["author_display_name"]
            assert imported_post["note"] == original_post["note"]

        new_conn.close()
        new_db_path.unlink(missing_ok=True)