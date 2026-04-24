"""ExportService and ImportService for data portability.

IMEX-01: User can export stored posts to JSON format.
IMEX-02: User can export stored posts to CSV format.
IMEX-03: User can import posts from JSON export.

D-03: JSON format: {version: "1.0", exported_at: ISO_DATE, source: "xbm", posts: [...]}
D-03: CSV format: Core fields only (x_post_id, text, author_username, author_display_name, created_at, note)

Usage:
    from src.services.export import ExportService, ImportService
    from src.repositories.posts import PostsRepository
    from src.db import get_connection

    conn = get_connection()
    repo = PostsRepository(conn)

    # Export to JSON
    export_service = ExportService(repo)
    result = export_service.export_json(Path("export.json"))

    # Export to CSV
    result = export_service.export_csv(Path("export.csv"))

    # Import from JSON
    import_service = ImportService(repo)
    result = import_service.import_json(Path("export.json"), conflict="skip")
"""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..repositories.posts import PostsRepository


@dataclass
class ExportResult:
    """Result of an export operation.

    Attributes:
        path: Path to the exported file.
        post_count: Number of posts exported.
        exported_at: ISO timestamp when export was created.
    """
    path: Path
    post_count: int
    exported_at: str


@dataclass
class ImportResult:
    """Result of an import operation.

    Attributes:
        imported_count: Number of posts successfully imported.
        skipped_count: Number of posts skipped (existing with conflict='skip').
        error_count: Number of posts that failed to import.
        errors: List of error messages for failed imports.
    """
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


class ExportService:
    """Service for exporting posts to JSON and CSV formats.

    Features:
    - JSON export with metadata wrapper (version, exported_at, source, post_count)
    - CSV export with core fields only (no arrays)
    - UTF-8 encoding for international content
    - Creates parent directories if needed
    """

    VERSION = "1.0"
    SOURCE = "xbm"

    # Core fields for CSV export (excludes media_urls, link_urls arrays)
    CSV_FIELDS = [
        "x_post_id",
        "text",
        "author_username",
        "author_display_name",
        "created_at",
        "note",
    ]

    def __init__(self, repo: PostsRepository):
        """Initialize export service with repository.

        Args:
            repo: PostsRepository for fetching posts.
        """
        self._repo = repo

    def export_json(self, output_path: Path) -> ExportResult:
        """Export all posts to JSON with metadata wrapper.

        D-03: JSON format includes version, exported_at, source, post_count, posts.
        IMEX-01: User can export stored posts to JSON format.

        Args:
            output_path: Path to write JSON file.

        Returns:
            ExportResult with path, count, and timestamp.
        """
        # Fetch all posts
        posts = self._repo.get_all(limit=999999)

        # Build export data structure per D-03
        exported_at = datetime.now(timezone.utc).isoformat()
        export_data = {
            "version": self.VERSION,
            "exported_at": exported_at,
            "source": self.SOURCE,
            "post_count": len(posts),
            "posts": [self._format_post_for_export(post) for post in posts]
        }

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with UTF-8 encoding and readable formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return ExportResult(
            path=output_path,
            post_count=len(posts),
            exported_at=exported_at
        )

    def export_csv(self, output_path: Path) -> ExportResult:
        """Export posts to CSV with core fields only.

        D-03: CSV format includes core fields only (id, text, author_username,
              author_display_name, created_at, note).
        IMEX-02: User can export stored posts to CSV format.

        Args:
            output_path: Path to write CSV file.

        Returns:
            ExportResult with path and count.
        """
        # Fetch all posts
        posts = self._repo.get_all(limit=999999)

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write CSV with UTF-8 encoding
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS, extrasaction='ignore')
            writer.writeheader()

            for post in posts:
                writer.writerow(self._format_post_for_csv(post))

        return ExportResult(
            path=output_path,
            post_count=len(posts),
            exported_at=datetime.now(timezone.utc).isoformat()
        )

    def _format_post_for_export(self, post: dict[str, Any]) -> dict[str, Any]:
        """Format post for JSON export.

        Ensures all fields are JSON-serializable and datetime strings are ISO format.

        Args:
            post: Post dict from repository.

        Returns:
            Post dict ready for JSON serialization.
        """
        formatted = {
            "x_post_id": post.get("x_post_id", ""),
            "created_at": post.get("created_at", ""),
            "text": post.get("text", ""),
            "author_id": post.get("author_id", ""),
            "author_username": post.get("author_username", ""),
            "author_display_name": post.get("author_display_name"),
            "media_urls": post.get("media_urls", []),
            "link_urls": post.get("link_urls", []),
            "bookmarked_at": post.get("bookmarked_at"),
            "note": post.get("note"),
        }

        # Convert None to null for JSON (handled automatically by json.dump)
        # Ensure arrays are lists (not JSON strings)
        if isinstance(formatted["media_urls"], str):
            formatted["media_urls"] = json.loads(formatted["media_urls"])
        if isinstance(formatted["link_urls"], str):
            formatted["link_urls"] = json.loads(formatted["link_urls"])

        return formatted

    def _format_post_for_csv(self, post: dict[str, Any]) -> dict[str, str]:
        """Format post for CSV export with core fields only.

        Extracts only CSV_FIELDS and converts None to empty string.

        Args:
            post: Post dict from repository.

        Returns:
            Dict with CSV_FIELDS keys, values as strings.
        """
        return {
            "x_post_id": post.get("x_post_id", ""),
            "text": post.get("text", ""),
            "author_username": post.get("author_username", ""),
            "author_display_name": post.get("author_display_name", "") or "",
            "created_at": post.get("created_at", ""),
            "note": post.get("note") or "",  # NULL becomes empty string
        }


class ImportService:
    """Service for importing posts from JSON export files.

    Features:
    - Validates version and source fields
    - Handles skip vs update conflict resolution
    - Captures errors without crashing
    - Preserves data integrity
    """

    SUPPORTED_VERSION = "1.0"
    EXPECTED_SOURCE = "xbm"

    # Required fields for a valid post import
    REQUIRED_POST_FIELDS = ["x_post_id", "text", "author_id", "author_username"]

    def __init__(self, repo: PostsRepository):
        """Initialize import service with repository.

        Args:
            repo: PostsRepository for importing posts.
        """
        self._repo = repo

    def import_json(
        self,
        input_path: Path,
        conflict: str = "skip"
    ) -> ImportResult:
        """Import posts from JSON export file.

        D-03: Import supports JSON format only.
        IMEX-03: User can import posts from JSON export.

        Args:
            input_path: Path to JSON export file.
            conflict: "skip" to skip existing posts, "update" to update them.

        Returns:
            ImportResult with imported and skipped counts.

        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If version or source fields are invalid.
            json.JSONDecodeError: If file is not valid JSON.
        """
        result = ImportResult()

        # Read and parse JSON file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate version
        if data.get("version") != self.SUPPORTED_VERSION:
            raise ValueError(
                f"Unsupported export version: {data.get('version')}. "
                f"Expected {self.SUPPORTED_VERSION}."
            )

        # Validate source
        if data.get("source") != self.EXPECTED_SOURCE:
            raise ValueError(
                f"Invalid source: {data.get('source')}. "
                f"Expected {self.EXPECTED_SOURCE}."
            )

        # Process posts
        for post in data.get("posts", []):
            try:
                # Validate required fields
                if not self._validate_post(post):
                    result.error_count += 1
                    result.errors.append(
                        f"Missing required fields in post: {post.get('x_post_id', 'unknown')}"
                    )
                    continue

                # Check if post exists
                existing = self._repo.get_by_id(post["x_post_id"])

                if existing and conflict == "skip":
                    result.skipped_count += 1
                    continue

                # Import or update post
                self._repo.upsert_post(self._format_post_for_import(post))
                result.imported_count += 1

            except Exception as e:
                result.error_count += 1
                result.errors.append(f"Error importing post {post.get('x_post_id', 'unknown')}: {str(e)}")

        return result

    def _validate_post(self, post: dict[str, Any]) -> bool:
        """Validate post has required fields.

        Args:
            post: Post dict from JSON.

        Returns:
            True if valid, False otherwise.
        """
        for field in self.REQUIRED_POST_FIELDS:
            if field not in post or post[field] is None:
                return False
        return True

    def _format_post_for_import(self, post: dict[str, Any]) -> dict[str, Any]:
        """Format post from JSON for repository upsert.

        Ensures all fields are present with appropriate defaults.

        Args:
            post: Post dict from JSON.

        Returns:
            Post dict ready for upsert_post.
        """
        return {
            "x_post_id": post.get("x_post_id", ""),
            "created_at": post.get("created_at", ""),
            "text": post.get("text", ""),
            "author_id": post.get("author_id", ""),
            "author_username": post.get("author_username", ""),
            "author_display_name": post.get("author_display_name"),
            "media_urls": post.get("media_urls", []),
            "link_urls": post.get("link_urls", []),
            "bookmarked_at": post.get("bookmarked_at"),
            "note": post.get("note"),
        }