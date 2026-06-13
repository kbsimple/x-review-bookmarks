"""CLI integration tests for xbm export-static command.

EXPORT-01 through EXPORT-04: CLI command creates output directory with all files.

Uses typer.testing.CliRunner -- same pattern as test_cli.py.
Database is a real temp file (CLI calls init_database with a file path).
"""

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli.main import app
from src.db import init_database


def _make_temp_db(tmp_path: Path) -> Path:
    """Create a minimal seeded database file for CLI tests.

    Returns:
        Path to the database file.
    """
    db_path = tmp_path / "test_bookmarks.db"
    conn = init_database(db_path)
    conn.execute("""
        INSERT INTO posts (x_post_id, created_at, text, author_id, author_username,
            author_display_name, media_urls, link_urls, bookmarked_at)
        VALUES ('cli_post_001', '2024-06-01T10:00:00Z', 'CLI test post content',
            'user_001', 'cliuser', 'CLI User', '[]', '[]', '2024-06-02T08:00:00Z')
    """)
    conn.commit()
    conn.close()
    return db_path


runner = CliRunner()


class TestExportStaticCLI:
    """Integration tests for the export-static CLI command."""

    def test_export_static_command_creates_output_dir(self, tmp_path):
        """xbm export-static --output <tmp_path/out> exits 0 and creates directory with files."""
        db_path = _make_temp_db(tmp_path)
        out_dir = tmp_path / "export-out"

        result = runner.invoke(
            app,
            ["export-static", "--output", str(out_dir), "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert out_dir.exists()
        assert (out_dir / "posts.json").exists()
        assert (out_dir / "index.html").exists()
        assert (out_dir / "netlify.toml").exists()

    def test_export_static_with_custom_output_path(self, tmp_path):
        """--output flag routes all files to the specified directory."""
        db_path = _make_temp_db(tmp_path)
        custom_out = tmp_path / "custom" / "nested" / "export"

        result = runner.invoke(
            app,
            ["export-static", "--output", str(custom_out), "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert custom_out.exists()
        assert (custom_out / "posts.json").exists()

    def test_export_static_prints_deployment_instructions(self, tmp_path):
        """CLI output contains 'netlify' in the deployment instructions panel."""
        db_path = _make_temp_db(tmp_path)
        out_dir = tmp_path / "deploy-test"

        result = runner.invoke(
            app,
            ["export-static", "--output", str(out_dir), "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert "netlify" in result.output.lower()

    def test_export_static_summary_table_shows_file_sizes(self, tmp_path):
        """CLI output contains 'posts.json' in the summary table."""
        db_path = _make_temp_db(tmp_path)
        out_dir = tmp_path / "summary-test"

        result = runner.invoke(
            app,
            ["export-static", "--output", str(out_dir), "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert "posts.json" in result.output
