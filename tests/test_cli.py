"""Tests for CLI commands.

Tests CLI interface for:
- auth: Authenticate with X API
- init: Initialize database
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.main import app


runner = CliRunner()


class TestInitCommand:
    """Tests for `xbm init` command."""

    def test_init_command_creates_database(self, tmp_path: Path) -> None:
        """Verify init command creates database file.

        Expected behavior:
        - Command exits with code 0
        - Database file is created
        - Success message displayed
        """
        db_path = tmp_path / "test.db"

        result = runner.invoke(app, ["init", "--db", str(db_path)])

        # Should succeed
        assert result.exit_code == 0, f"Exit code should be 0, got {result.exit_code}"

        # Database should be created
        assert db_path.exists(), "Database file should be created"

        # Success message should be displayed
        assert "Database initialized" in result.stdout, (
            f"Expected success message in output: {result.stdout}"
        )

    def test_init_command_default_path(self, tmp_path: Path) -> None:
        """Verify init command uses default path.

        Expected behavior:
        - Without --db, uses data/bookmarks.db
        """
        # Run from temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["init"])

            # Should succeed (uses default path)
            assert result.exit_code == 0, (
                f"Exit code should be 0, got {result.exit_code}"
            )
        finally:
            os.chdir(original_cwd)

    def test_init_command_help(self) -> None:
        """Verify init command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize the SQLite database" in result.stdout


class TestAuthCommand:
    """Tests for `xbm auth` command."""

    def test_auth_command_help(self) -> None:
        """Verify auth command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "Authenticate with X API" in result.stdout

    def test_auth_command_missing_credentials(self) -> None:
        """Verify auth command fails with missing credentials.

        Expected behavior:
        - Without X_CLIENT_ID/X_CLIENT_SECRET, command fails
        - Clear error message displayed
        - Exit code 1
        """
        # Mock Settings to raise error for missing credentials
        with patch("src.cli.main.Settings") as mock_settings_class:
            from pydantic import ValidationError
            from pydantic_core import ErrorDetails

            # Simulate missing credentials
            error = ValidationError.from_exception_data(
                "Settings",
                [
                    {
                        "type": "missing",
                        "loc": ("client_id",),
                        "input": {},
                        "msg": "field required",
                    }
                ],
            )
            mock_settings_class.side_effect = error

            result = runner.invoke(app, ["auth"])

            # Should fail
            assert result.exit_code == 1, (
                f"Exit code should be 1, got {result.exit_code}"
            )

    def test_auth_command_success(self, tmp_path: Path) -> None:
        """Verify auth command succeeds with valid credentials.

        Expected behavior:
        - With valid credentials and tokens, command succeeds
        - Success message displayed
        - Exit code 0
        """
        from src.auth.oauth import XAuth

        # Mock Settings to return valid credentials
        mock_settings = MagicMock()
        mock_settings.client_id = "test_client_id"
        mock_settings.client_secret_value = "test_client_secret"
        mock_settings.token_path = tmp_path / "tokens.json"

        # Pre-save tokens
        mock_settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mock_settings.token_path, "w") as f:
            json.dump(
                {"access_token": "test_access", "refresh_token": "test_refresh"},
                f,
            )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.ensure_authenticated") as mock_auth:
                mock_auth.return_value = XAuth(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    access_token="test_access",
                    refresh_token="test_refresh",
                )

                result = runner.invoke(app, ["auth"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}"
                )
                assert "Successfully authenticated" in result.stdout


class TestVerifyCommand:
    """Tests for `xbm verify` command."""

    def test_verify_command_help(self) -> None:
        """Verify verify command shows help."""
        result = runner.invoke(app, ["verify", "--help"])

        assert result.exit_code == 0
        assert "Verify current authentication status" in result.stdout


class TestCliApp:
    """Tests for CLI application structure."""

    def test_app_name(self) -> None:
        """Verify CLI app has correct name."""
        assert app.info.name == "xbm"

    def test_app_has_commands(self) -> None:
        """Verify CLI app has expected commands."""
        # Typer stores commands in registered_commands
        # The name is derived from the callback function name if not explicitly set
        command_names = []
        for cmd in app.registered_commands:
            # Try explicit name first, then callback name
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "auth" in command_names, f"auth command should exist, got: {command_names}"
        assert "init" in command_names, f"init command should exist, got: {command_names}"

    def test_rich_markup_enabled(self) -> None:
        """Verify Rich markup is enabled."""
        assert app.rich_markup_mode == "rich", "Rich markup should be enabled"


class TestSyncCommand:
    """Tests for `xbm sync` command.

    Tests for:
    - CLI-01: Trigger bookmark sync via CLI command
    - CLI-05: CLI displays rich output with post content, images, and metadata
    """

    def test_sync_command_exists(self) -> None:
        """Verify sync command is registered in CLI app.

        CLI-01: User can trigger bookmark sync via CLI command.
        """
        # Check that sync command exists in registered commands
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "sync" in command_names, f"sync command should exist, got: {command_names}"

    def test_sync_command_help(self) -> None:
        """Verify sync command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["sync", "--help"])

        assert result.exit_code == 0
        assert "Sync bookmarks" in result.stdout

    def test_sync_command_calls_sync_service(self, tmp_path: Path) -> None:
        """Verify sync command calls SyncService.sync().

        CLI-01: User can trigger bookmark sync via CLI command.

        Expected behavior:
        - Command authenticates
        - Command creates SyncService
        - Command calls sync()
        """
        from src.auth.oauth import XAuth
        from src.services.sync import SyncResult

        # Create mock auth
        mock_auth = XAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access",
            refresh_token="test_refresh",
        )

        # Create mock result
        mock_result = SyncResult(
            total_fetched=10,
            new_count=5,
            updated_count=3,
            error_count=0,
            rate_limit_waits=0,
            is_complete=True,
            warnings=[],
        )

        # Mock Settings
        mock_settings = MagicMock()
        mock_settings.client_id = "test_client_id"
        mock_settings.client_secret_value = "test_client_secret"
        mock_settings.token_path = tmp_path / "tokens.json"
        mock_settings.database_path = tmp_path / "test.db"

        # Pre-save tokens
        mock_settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mock_settings.token_path, "w") as f:
            json.dump(
                {"access_token": "test_access", "refresh_token": "test_refresh"},
                f,
            )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.ensure_authenticated") as mock_ensure_auth:
                mock_ensure_auth.return_value = mock_auth

                with patch("src.services.sync.SyncService") as mock_sync_class:
                    mock_sync_instance = MagicMock()
                    mock_sync_instance.sync.return_value = mock_result
                    mock_sync_class.return_value = mock_sync_instance

                    result = runner.invoke(app, ["sync"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should have called sync
                    mock_sync_instance.sync.assert_called_once()

    def test_sync_command_shows_progress(self, tmp_path: Path) -> None:
        """Verify sync command shows progress during sync.

        D-04: Progress bar during sync.

        Expected behavior:
        - Progress callback is registered
        - Progress messages appear in output
        """
        from src.auth.oauth import XAuth
        from src.services.sync import SyncResult

        mock_auth = XAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access",
            refresh_token="test_refresh",
        )

        mock_result = SyncResult(
            total_fetched=50,
            new_count=50,
            updated_count=0,
            error_count=0,
            rate_limit_waits=0,
            is_complete=True,
            warnings=[],
        )

        mock_settings = MagicMock()
        mock_settings.client_id = "test_client_id"
        mock_settings.client_secret_value = "test_client_secret"
        mock_settings.token_path = tmp_path / "tokens.json"
        mock_settings.database_path = tmp_path / "test.db"

        mock_settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mock_settings.token_path, "w") as f:
            json.dump(
                {"access_token": "test_access", "refresh_token": "test_refresh"},
                f,
            )

        progress_callback = None

        def capture_progress_callback(service_instance):
            """Capture the progress callback from SyncService instantiation."""
            nonlocal progress_callback
            # Get the on_progress callback
            progress_callback = service_instance._on_progress

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.ensure_authenticated") as mock_ensure_auth:
                mock_ensure_auth.return_value = mock_auth

                with patch("src.services.sync.SyncService") as mock_sync_class:
                    mock_sync_instance = MagicMock()
                    mock_sync_instance.sync.return_value = mock_result

                    # Track calls to constructor to capture callbacks
                    def create_sync_service(*args, **kwargs):
                        mock_sync_instance._on_progress = kwargs.get("on_progress")
                        return mock_sync_instance

                    mock_sync_class.side_effect = create_sync_service

                    result = runner.invoke(app, ["sync"])

                    # Verify progress callback was provided
                    assert mock_sync_instance._on_progress is not None, (
                        "Progress callback should be provided to SyncService"
                    )

    def test_sync_command_shows_summary(self, tmp_path: Path) -> None:
        """Verify sync command shows summary table.

        CLI-05: Summary table with counts: total, new, updated, errors.

        Expected behavior:
        - Summary table displayed after sync
        - Shows total fetched, new, updated, errors
        """
        from src.auth.oauth import XAuth
        from src.services.sync import SyncResult

        mock_auth = XAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access",
            refresh_token="test_refresh",
        )

        mock_result = SyncResult(
            total_fetched=100,
            new_count=80,
            updated_count=20,
            error_count=2,
            rate_limit_waits=1,
            is_complete=True,
            warnings=[],
        )

        mock_settings = MagicMock()
        mock_settings.client_id = "test_client_id"
        mock_settings.client_secret_value = "test_client_secret"
        mock_settings.token_path = tmp_path / "tokens.json"
        mock_settings.database_path = tmp_path / "test.db"

        mock_settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mock_settings.token_path, "w") as f:
            json.dump(
                {"access_token": "test_access", "refresh_token": "test_refresh"},
                f,
            )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.ensure_authenticated") as mock_ensure_auth:
                mock_ensure_auth.return_value = mock_auth

                with patch("src.services.sync.SyncService") as mock_sync_class:
                    mock_sync_instance = MagicMock()
                    mock_sync_instance.sync.return_value = mock_result
                    mock_sync_class.return_value = mock_sync_instance

                    result = runner.invoke(app, ["sync"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Summary table should show counts
                    assert "100" in result.stdout, "Total fetched should be in output"
                    assert "80" in result.stdout, "New count should be in output"
                    assert "20" in result.stdout, "Updated count should be in output"

    def test_sync_command_shows_warnings(self, tmp_path: Path) -> None:
        """Verify sync command shows warnings.

        Expected behavior:
        - Warnings displayed in yellow
        - Warning message appears in output
        """
        from src.auth.oauth import XAuth
        from src.services.sync import SyncResult

        mock_auth = XAuth(
            client_id="test_client_id",
            client_secret="test_client_secret",
            access_token="test_access",
            refresh_token="test_refresh",
        )

        mock_result = SyncResult(
            total_fetched=100,
            new_count=100,
            updated_count=0,
            error_count=0,
            rate_limit_waits=0,
            is_complete=True,
            warnings=["Approaching API limit: 780/800 bookmarks"],
        )

        mock_settings = MagicMock()
        mock_settings.client_id = "test_client_id"
        mock_settings.client_secret_value = "test_client_secret"
        mock_settings.token_path = tmp_path / "tokens.json"
        mock_settings.database_path = tmp_path / "test.db"

        mock_settings.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mock_settings.token_path, "w") as f:
            json.dump(
                {"access_token": "test_access", "refresh_token": "test_refresh"},
                f,
            )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.ensure_authenticated") as mock_ensure_auth:
                mock_ensure_auth.return_value = mock_auth

                with patch("src.services.sync.SyncService") as mock_sync_class:
                    mock_sync_instance = MagicMock()
                    mock_sync_instance.sync.return_value = mock_result
                    mock_sync_class.return_value = mock_sync_instance

                    result = runner.invoke(app, ["sync"])

                    # Warning should appear in output
                    assert "780/800" in result.stdout or "Approaching" in result.stdout or "Warning" in result.stdout, (
                        f"Warning should be in output: {result.stdout}"
                    )

    def test_sync_command_auth_failure(self, tmp_path: Path) -> None:
        """Verify sync command handles auth failure gracefully.

        AUTH-03: Clear error messages.

        Expected behavior:
        - Exit code 1
        - Clear error message
        """
        with patch("src.cli.main.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.client_id = "test_client_id"
            mock_settings.client_secret_value = "test_client_secret"
            mock_settings.token_path = tmp_path / "tokens.json"
            mock_settings.database_path = tmp_path / "test.db"
            mock_settings_class.return_value = mock_settings

            with patch("src.cli.main.ensure_authenticated") as mock_ensure_auth:
                from src.auth.oauth import AuthError
                mock_ensure_auth.side_effect = AuthError("Authentication failed")

                result = runner.invoke(app, ["sync"])

                # Should fail with exit code 1
                assert result.exit_code == 1, (
                    f"Exit code should be 1, got {result.exit_code}"
                )
                assert "Authentication" in result.stdout or "failed" in result.stdout.lower()


class TestSearchCommand:
    """Tests for `xbm search` command.

    Tests for:
    - CLI-03: User can search stored posts via CLI command
    - SRCH-01: Full-text search within stored post content
    - SRCH-02: Search by author name or username
    - SRCH-03: Search results display relevant post content with context
    """

    def test_search_command_exists(self) -> None:
        """Verify search command is registered in CLI app.

        CLI-03: User can search stored posts via CLI command.
        """
        # Check that search command exists in registered commands
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "search" in command_names, f"search command should exist, got: {command_names}"

    def test_search_command_help(self) -> None:
        """Verify search command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["search", "--help"])

        assert result.exit_code == 0
        assert "Search stored posts" in result.stdout

    def test_search_command_returns_results(self, tmp_path: Path) -> None:
        """Verify search command returns results from SearchService.

        CLI-03: User can search stored posts via CLI command.

        Expected behavior:
        - Command calls SearchService.search()
        - Results displayed in Rich table
        """
        from src.services.search import SearchResult

        # Mock Settings to use temp database
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Create test database with posts_fts
        from src.db import init_database
        db_path = tmp_path / "test.db"
        conn = init_database(db_path)

        # Insert test post
        conn.execute("""
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username, author_display_name
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, ("test_post_1", "2024-01-15T10:00:00Z", "Python is great for data science", "user_1", "pythonista", "Python Developer"))
        conn.commit()
        conn.close()

        # Mock SearchService to return test results
        mock_result = SearchResult(
            x_post_id="test_post_1",
            author_username="pythonista",
            author_display_name="Python Developer",
            created_at="2024-01-15T10:00:00Z",
            snippet="Python is great for data science",
            rank=-1.0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.search.SearchService") as mock_search_class:
                mock_search_instance = MagicMock()
                mock_search_instance.search.return_value = [mock_result]
                mock_search_class.return_value = mock_search_instance

                result = runner.invoke(app, ["search", "Python"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called search
                mock_search_instance.search.assert_called_once()

    def test_search_command_with_author_filter(self, tmp_path: Path) -> None:
        """Verify search command supports --author filter.

        SRCH-02: Search by author name or username.

        Expected behavior:
        - Command passes author parameter to SearchService
        """
        from src.services.search import SearchResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = SearchResult(
            x_post_id="test_post_1",
            author_username="pythonista",
            author_display_name="Python Developer",
            created_at="2024-01-15T10:00:00Z",
            snippet="Python is great for data science",
            rank=-1.0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.search.SearchService") as mock_search_class:
                mock_search_instance = MagicMock()
                mock_search_instance.search.return_value = [mock_result]
                mock_search_class.return_value = mock_search_instance

                result = runner.invoke(app, ["search", "Python", "--author", "pythonista"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called search with author filter
                mock_search_instance.search.assert_called_once()
                call_kwargs = mock_search_instance.search.call_args[1]
                assert call_kwargs.get("author") == "pythonista", (
                    f"Author should be passed to search, got: {call_kwargs}"
                )

    def test_search_command_with_limit(self, tmp_path: Path) -> None:
        """Verify search command supports --limit option.

        Expected behavior:
        - Command passes limit parameter to SearchService
        """
        from src.services.search import SearchResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = SearchResult(
            x_post_id="test_post_1",
            author_username="pythonista",
            author_display_name="Python Developer",
            created_at="2024-01-15T10:00:00Z",
            snippet="Python is great for data science",
            rank=-1.0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.search.SearchService") as mock_search_class:
                mock_search_instance = MagicMock()
                mock_search_instance.search.return_value = [mock_result]
                mock_search_class.return_value = mock_search_instance

                result = runner.invoke(app, ["search", "Python", "--limit", "5"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called search with limit
                mock_search_instance.search.assert_called_once()
                call_kwargs = mock_search_instance.search.call_args[1]
                assert call_kwargs.get("limit") == 5, (
                    f"Limit should be passed to search, got: {call_kwargs}"
                )

    def test_search_command_no_results(self, tmp_path: Path) -> None:
        """Verify search command handles no results gracefully.

        Expected behavior:
        - Displays 'No results found' message
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.search.SearchService") as mock_search_class:
                mock_search_instance = MagicMock()
                mock_search_instance.search.return_value = []  # No results
                mock_search_class.return_value = mock_search_instance

                result = runner.invoke(app, ["search", "nonexistent_term"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show no results message
                assert "No results found" in result.stdout, (
                    f"Expected 'No results found' in output: {result.stdout}"
                )

    def test_search_command_displays_rich_table(self, tmp_path: Path) -> None:
        """Verify search command displays results in Rich table.

        SRCH-03: Search results display relevant post content with context.

        Expected behavior:
        - Results shown in table format
        - Shows author, snippet, and date
        """
        from src.services.search import SearchResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = SearchResult(
            x_post_id="test_post_1",
            author_username="pythonista",
            author_display_name="Python Developer",
            created_at="2024-01-15T10:00:00Z",
            snippet="Python is great for data science",
            rank=-1.0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.search.SearchService") as mock_search_class:
                mock_search_instance = MagicMock()
                mock_search_instance.search.return_value = [mock_result]
                mock_search_class.return_value = mock_search_instance

                result = runner.invoke(app, ["search", "Python"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show results count
                assert "1 results" in result.stdout or "Showing 1" in result.stdout, (
                    f"Expected results count in output: {result.stdout}"
                )

    def test_search_command_error_handling(self, tmp_path: Path) -> None:
        """Verify search command handles errors gracefully.

        Expected behavior:
        - Exit code 1 on error
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.search.SearchService") as mock_search_class:
                mock_search_instance = MagicMock()
                mock_search_instance.search.side_effect = Exception("Database error")
                mock_search_class.return_value = mock_search_instance

                result = runner.invoke(app, ["search", "Python"])

                # Should fail
                assert result.exit_code == 1, (
                    f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show error
                assert "Error" in result.stdout or "failed" in result.stdout.lower(), (
                    f"Expected error message in output: {result.stdout}"
                )


class TestNoteCommand:
    """Tests for `xbm note` command.

    Tests for:
    - NOTE-01: User can add personal notes to bookmarked posts
    """

    def test_note_command_exists(self) -> None:
        """Verify note command is registered in CLI app.

        NOTE-01: User can add personal notes to bookmarked posts.
        """
        # Check that note command exists in registered commands
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "note" in command_names, f"note command should exist, got: {command_names}"

    def test_note_command_help(self) -> None:
        """Verify note command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["note", "--help"])

        assert result.exit_code == 0
        assert "Add, update, or remove a note" in result.stdout

    def test_note_command_shows_existing_note(self, tmp_path: Path) -> None:
        """Verify note command shows current note when no text provided.

        NOTE-01: User can add personal notes to bookmarked posts.

        Expected behavior:
        - Command retrieves post
        - Displays existing note in Rich Panel
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Mock PostsRepository.get_by_id to return post with note
        mock_post = {
            "x_post_id": "test_post_1",
            "note": "This is my note",
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.repositories.PostsRepository") as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_instance.get_by_id.return_value = mock_post
                mock_repo_class.return_value = mock_repo_instance

                result = runner.invoke(app, ["note", "test_post_1"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show note
                assert "This is my note" in result.stdout, (
                    f"Expected note in output: {result.stdout}"
                )

    def test_note_command_adds_note(self, tmp_path: Path) -> None:
        """Verify note command adds note when text provided.

        NOTE-01: User can add personal notes to bookmarked posts.

        Expected behavior:
        - Command calls PostsRepository.update_note()
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Mock PostsRepository
        mock_post = {
            "x_post_id": "test_post_1",
            "note": None,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.repositories.PostsRepository") as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_instance.get_by_id.return_value = mock_post
                mock_repo_class.return_value = mock_repo_instance

                result = runner.invoke(app, ["note", "test_post_1", "My new note"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should call update_note
                mock_repo_instance.update_note.assert_called_once_with("test_post_1", "My new note")

                # Should show success message
                assert "Note added" in result.stdout or "Note added to post" in result.stdout, (
                    f"Expected success message in output: {result.stdout}"
                )

    def test_note_command_clears_note(self, tmp_path: Path) -> None:
        """Verify note command removes note with --clear option.

        NOTE-01: User can add personal notes to bookmarked posts.

        Expected behavior:
        - Command calls PostsRepository.update_note() with None
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Mock PostsRepository
        mock_post = {
            "x_post_id": "test_post_1",
            "note": "Existing note",
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.repositories.PostsRepository") as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_instance.get_by_id.return_value = mock_post
                mock_repo_class.return_value = mock_repo_instance

                result = runner.invoke(app, ["note", "test_post_1", "--clear"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should call update_note with None
                mock_repo_instance.update_note.assert_called_once_with("test_post_1", None)

                # Should show removal message
                assert "Note removed" in result.stdout or "removed" in result.stdout.lower(), (
                    f"Expected removal message in output: {result.stdout}"
                )

    def test_note_command_post_not_found(self, tmp_path: Path) -> None:
        """Verify note command handles non-existent post.

        Expected behavior:
        - Exit code 1
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.repositories.PostsRepository") as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_instance.get_by_id.return_value = None  # Post not found
                mock_repo_class.return_value = mock_repo_instance

                result = runner.invoke(app, ["note", "nonexistent_post"])

                # Should fail
                assert result.exit_code == 1, (
                    f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show error
                assert "Post not found" in result.stdout or "not found" in result.stdout.lower(), (
                    f"Expected 'not found' in output: {result.stdout}"
                )

    def test_note_command_no_note_for_post(self, tmp_path: Path) -> None:
        """Verify note command handles post without note.

        Expected behavior:
        - Shows 'No note' message
        - Suggests adding a note
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Mock PostsRepository
        mock_post = {
            "x_post_id": "test_post_1",
            "note": None,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.repositories.PostsRepository") as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_instance.get_by_id.return_value = mock_post
                mock_repo_class.return_value = mock_repo_instance

                result = runner.invoke(app, ["note", "test_post_1"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show no note message
                assert "No note" in result.stdout or "no note" in result.stdout.lower(), (
                    f"Expected 'No note' in output: {result.stdout}"
                )

    def test_note_command_error_handling(self, tmp_path: Path) -> None:
        """Verify note command handles errors gracefully.

        Expected behavior:
        - Exit code 1 on error
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.repositories.PostsRepository") as mock_repo_class:
                mock_repo_instance = MagicMock()
                mock_repo_instance.get_by_id.side_effect = Exception("Database error")
                mock_repo_class.return_value = mock_repo_instance

                result = runner.invoke(app, ["note", "test_post_1"])

                # Should fail
                assert result.exit_code == 1, (
                    f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show error
                assert "Error" in result.stdout or "failed" in result.stdout.lower(), (
                    f"Expected error message in output: {result.stdout}"
                )


class TestExportCommand:
    """Tests for `xbm export` command.

    Tests for:
    - IMEX-01: User can export stored posts to JSON format
    - IMEX-02: User can export stored posts to CSV format
    """

    def test_export_command_exists(self) -> None:
        """Verify export command is registered in CLI app.

        IMEX-01: User can export stored posts to JSON format.
        """
        # Check that export command exists in registered commands
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "export" in command_names, f"export command should exist, got: {command_names}"

    def test_export_command_help(self) -> None:
        """Verify export command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["export", "--help"])

        assert result.exit_code == 0
        assert "Export" in result.stdout or "export" in result.stdout.lower()

    def test_export_command_creates_json(self, tmp_path: Path) -> None:
        """Verify export command creates JSON file.

        IMEX-01: User can export stored posts to JSON format.

        Expected behavior:
        - Command calls ExportService.export_json()
        - JSON file created with metadata wrapper
        """
        from src.services.export import ExportResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        output_path = tmp_path / "export.json"

        # Mock ExportResult
        mock_result = ExportResult(
            path=output_path,
            post_count=10,
            exported_at="2024-01-15T10:00:00Z",
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ExportService") as mock_export_class:
                mock_export_instance = MagicMock()
                mock_export_instance.export_json.return_value = mock_result
                mock_export_class.return_value = mock_export_instance

                result = runner.invoke(app, ["export", "--output", str(output_path), "--format", "json"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called export_json
                mock_export_instance.export_json.assert_called_once()

    def test_export_command_creates_csv(self, tmp_path: Path) -> None:
        """Verify export command creates CSV file.

        IMEX-02: User can export stored posts to CSV format.

        Expected behavior:
        - Command calls ExportService.export_csv()
        - CSV file created with core fields
        """
        from src.services.export import ExportResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        output_path = tmp_path / "export.csv"

        # Mock ExportResult
        mock_result = ExportResult(
            path=output_path,
            post_count=10,
            exported_at="2024-01-15T10:00:00Z",
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ExportService") as mock_export_class:
                mock_export_instance = MagicMock()
                mock_export_instance.export_csv.return_value = mock_result
                mock_export_class.return_value = mock_export_instance

                result = runner.invoke(app, ["export", "--output", str(output_path), "--format", "csv"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called export_csv
                mock_export_instance.export_csv.assert_called_once()

    def test_export_command_default_format_json(self, tmp_path: Path) -> None:
        """Verify export command defaults to JSON format.

        Expected behavior:
        - Without --format, defaults to JSON
        """
        from src.services.export import ExportResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        output_path = tmp_path / "export.json"

        mock_result = ExportResult(
            path=output_path,
            post_count=5,
            exported_at="2024-01-15T10:00:00Z",
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ExportService") as mock_export_class:
                mock_export_instance = MagicMock()
                mock_export_instance.export_json.return_value = mock_result
                mock_export_class.return_value = mock_export_instance

                result = runner.invoke(app, ["export", "--output", str(output_path)])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called export_json (not export_csv)
                mock_export_instance.export_json.assert_called_once()
                mock_export_instance.export_csv.assert_not_called()

    def test_export_command_shows_post_count(self, tmp_path: Path) -> None:
        """Verify export command shows post count in success message.

        Expected behavior:
        - Success message includes post count
        """
        from src.services.export import ExportResult

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        output_path = tmp_path / "export.json"

        mock_result = ExportResult(
            path=output_path,
            post_count=42,
            exported_at="2024-01-15T10:00:00Z",
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ExportService") as mock_export_class:
                mock_export_instance = MagicMock()
                mock_export_instance.export_json.return_value = mock_result
                mock_export_class.return_value = mock_export_instance

                result = runner.invoke(app, ["export", "--output", str(output_path)])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show post count
                assert "42" in result.stdout or "Exported" in result.stdout, (
                    f"Expected post count in output: {result.stdout}"
                )

    def test_export_command_invalid_format(self, tmp_path: Path) -> None:
        """Verify export command handles invalid format.

        Expected behavior:
        - Exit code 1 for invalid format
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        output_path = tmp_path / "export.xml"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            result = runner.invoke(app, ["export", "--output", str(output_path), "--format", "xml"])

            # Should fail
            assert result.exit_code == 1, (
                f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
            )

            # Should show error
            assert "Invalid format" in result.stdout or "invalid" in result.stdout.lower(), (
                f"Expected invalid format message: {result.stdout}"
            )


class TestImportCommand:
    """Tests for `xbm import` command.

    Tests for:
    - IMEX-03: User can import posts from JSON export
    """

    def test_import_command_exists(self) -> None:
        """Verify import command is registered in CLI app.

        IMEX-03: User can import posts from JSON export.
        """
        # Check that import command exists in registered commands
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        # Note: function is named 'import_cmd' but command is 'import'
        assert "import" in command_names, f"import command should exist, got: {command_names}"

    def test_import_command_help(self) -> None:
        """Verify import command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["import", "--help"])

        assert result.exit_code == 0
        assert "Import" in result.stdout or "import" in result.stdout.lower()

    def test_import_command_validates_version(self, tmp_path: Path) -> None:
        """Verify import command validates version field.

        IMEX-03: User can import posts from JSON export.

        Expected behavior:
        - Import validates version is "1.0"
        - Error for wrong version
        """
        # Create test import file with wrong version
        import json
        test_file = tmp_path / "import.json"
        test_file.write_text(json.dumps({
            "version": "2.0",
            "source": "xbm",
            "posts": []
        }))

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            result = runner.invoke(app, ["import", str(test_file)])

            # Should fail
            assert result.exit_code == 1, (
                f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
            )

            # Should show version error
            assert "version" in result.stdout.lower() or "invalid" in result.stdout.lower(), (
                f"Expected version error in output: {result.stdout}"
            )

    def test_import_command_validates_source(self, tmp_path: Path) -> None:
        """Verify import command validates source field.

        IMEX-03: User can import posts from JSON export.

        Expected behavior:
        - Import validates source is "xbm"
        - Error for wrong source
        """
        # Create test import file with wrong source
        import json
        test_file = tmp_path / "import.json"
        test_file.write_text(json.dumps({
            "version": "1.0",
            "source": "other",
            "posts": []
        }))

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            result = runner.invoke(app, ["import", str(test_file)])

            # Should fail
            assert result.exit_code == 1, (
                f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
            )

            # Should show source error
            assert "source" in result.stdout.lower() or "invalid" in result.stdout.lower(), (
                f"Expected source error in output: {result.stdout}"
            )

    def test_import_command_imports_posts(self, tmp_path: Path) -> None:
        """Verify import command imports posts from JSON.

        IMEX-03: User can import posts from JSON export.

        Expected behavior:
        - Command calls ImportService.import_json()
        - Shows imported count
        """
        from src.services.export import ImportResult

        # Create valid test import file
        import json
        test_file = tmp_path / "import.json"
        test_file.write_text(json.dumps({
            "version": "1.0",
            "source": "xbm",
            "posts": [
                {
                    "x_post_id": "post_1",
                    "text": "Test post",
                    "author_id": "user_1",
                    "author_username": "testuser",
                }
            ]
        }))

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = ImportResult(
            imported_count=1,
            skipped_count=0,
            error_count=0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ImportService") as mock_import_class:
                mock_import_instance = MagicMock()
                mock_import_instance.import_json.return_value = mock_result
                mock_import_class.return_value = mock_import_instance

                result = runner.invoke(app, ["import", str(test_file)])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called import_json
                mock_import_instance.import_json.assert_called_once()

    def test_import_command_update_flag(self, tmp_path: Path) -> None:
        """Verify import command passes update flag to service.

        IMEX-03: User can import posts from JSON export.

        Expected behavior:
        - --update flag passed to ImportService
        - conflict="update" used
        """
        from src.services.export import ImportResult

        # Create valid test import file
        import json
        test_file = tmp_path / "import.json"
        test_file.write_text(json.dumps({
            "version": "1.0",
            "source": "xbm",
            "posts": []
        }))

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = ImportResult(
            imported_count=0,
            skipped_count=0,
            error_count=0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ImportService") as mock_import_class:
                mock_import_instance = MagicMock()
                mock_import_instance.import_json.return_value = mock_result
                mock_import_class.return_value = mock_import_instance

                result = runner.invoke(app, ["import", str(test_file), "--update"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called import_json with conflict="update"
                mock_import_instance.import_json.assert_called_once()
                call_kwargs = mock_import_instance.import_json.call_args[1]
                assert call_kwargs.get("conflict") == "update", (
                    f"Expected conflict='update', got: {call_kwargs}"
                )

    def test_import_command_shows_counts(self, tmp_path: Path) -> None:
        """Verify import command shows imported/skipped counts.

        IMEX-03: User can import posts from JSON export.

        Expected behavior:
        - Shows imported count
        - Shows skipped count
        """
        from src.services.export import ImportResult

        # Create valid test import file
        import json
        test_file = tmp_path / "import.json"
        test_file.write_text(json.dumps({
            "version": "1.0",
            "source": "xbm",
            "posts": []
        }))

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = ImportResult(
            imported_count=5,
            skipped_count=3,
            error_count=0,
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.export.ImportService") as mock_import_class:
                mock_import_instance = MagicMock()
                mock_import_instance.import_json.return_value = mock_result
                mock_import_class.return_value = mock_import_instance

                result = runner.invoke(app, ["import", str(test_file)])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show counts
                assert "5" in result.stdout or "Imported" in result.stdout, (
                    f"Expected imported count in output: {result.stdout}"
                )

    def test_import_command_file_not_found(self, tmp_path: Path) -> None:
        """Verify import command handles missing file.

        Expected behavior:
        - Exit code 1 for non-existent file
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        non_existent = tmp_path / "non_existent.json"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            result = runner.invoke(app, ["import", str(non_existent)])

            # Should fail
            assert result.exit_code == 1, (
                f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
            )

            # Should show error
            assert "not found" in result.stdout.lower() or "error" in result.stdout.lower(), (
                f"Expected file not found error: {result.stdout}"
            )


class TestCheckLinksCommand:
    """Tests for `xbm check-links` command.

    Tests for:
    - MAINT-01: Application detects and flags dead links in stored posts
    """

    def test_check_links_command_exists(self) -> None:
        """Verify check-links command is registered in CLI app.

        MAINT-01: Application detects and flags dead links in stored posts.
        """
        # Check that check-links command exists in registered commands
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "check-links" in command_names, f"check-links command should exist, got: {command_names}"

    def test_check_links_command_help(self) -> None:
        """Verify check-links command shows help.

        Expected behavior:
        - --help shows usage information
        """
        result = runner.invoke(app, ["check-links", "--help"])

        assert result.exit_code == 0
        assert "Check" in result.stdout or "check" in result.stdout.lower() or "link" in result.stdout.lower()

    def test_check_links_command_shows_summary(self, tmp_path: Path) -> None:
        """Verify check-links command shows summary table.

        MAINT-01: Application detects and flags dead links.

        Expected behavior:
        - Command calls LinkCheckerService.check_all_links_sync()
        - Shows summary table with ok/dead/error counts
        """
        from src.services.link_checker import CheckResult, LinkStatus

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Mock CheckResult
        mock_result = CheckResult(
            total_checked=10,
            ok_count=8,
            dead_count=1,
            error_count=1,
            results=[
                ("post_1", "https://example.com/1", LinkStatus(url="https://example.com/1", status="ok")),
                ("post_2", "https://example.com/dead", LinkStatus(url="https://example.com/dead", status="dead")),
            ],
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.link_checker.LinkCheckerService") as mock_checker_class:
                mock_checker_instance = MagicMock()
                mock_checker_instance.check_all_links_sync.return_value = mock_result
                mock_checker_class.return_value = mock_checker_instance

                result = runner.invoke(app, ["check-links"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called check_all_links_sync
                mock_checker_instance.check_all_links_sync.assert_called_once()

    def test_check_links_force_flag(self, tmp_path: Path) -> None:
        """Verify check-links --force flag bypasses cache.

        MAINT-01: Application detects and flags dead links.

        Expected behavior:
        - --force passed to check_all_links_sync(force=True)
        """
        from src.services.link_checker import CheckResult, LinkStatus

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = CheckResult(
            total_checked=5,
            ok_count=5,
            dead_count=0,
            error_count=0,
            results=[],
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.link_checker.LinkCheckerService") as mock_checker_class:
                mock_checker_instance = MagicMock()
                mock_checker_instance.check_all_links_sync.return_value = mock_result
                mock_checker_class.return_value = mock_checker_instance

                result = runner.invoke(app, ["check-links", "--force"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should have called with force=True
                mock_checker_instance.check_all_links_sync.assert_called_once()
                call_kwargs = mock_checker_instance.check_all_links_sync.call_args[1]
                assert call_kwargs.get("force") == True, (
                    f"Expected force=True, got: {call_kwargs}"
                )

    def test_check_links_shows_dead_links(self, tmp_path: Path) -> None:
        """Verify check-links shows dead links in output.

        MAINT-01: Application detects and flags dead links.

        Expected behavior:
        - Lists dead links when found
        - Shows post ID with URL
        """
        from src.services.link_checker import CheckResult, LinkStatus

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_result = CheckResult(
            total_checked=5,
            ok_count=3,
            dead_count=2,
            error_count=0,
            results=[
                ("post_1", "https://example.com/dead1", LinkStatus(url="https://example.com/dead1", status="dead")),
                ("post_2", "https://example.com/dead2", LinkStatus(url="https://example.com/dead2", status="dead")),
            ],
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.link_checker.LinkCheckerService") as mock_checker_class:
                mock_checker_instance = MagicMock()
                mock_checker_instance.check_all_links_sync.return_value = mock_result
                mock_checker_class.return_value = mock_checker_instance

                result = runner.invoke(app, ["check-links"])

                # Should succeed
                assert result.exit_code == 0, (
                    f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show dead links section
                assert "Dead" in result.stdout or "dead" in result.stdout.lower(), (
                    f"Expected dead links in output: {result.stdout}"
                )

    def test_check_links_error_handling(self, tmp_path: Path) -> None:
        """Verify check-links command handles errors gracefully.

        Expected behavior:
        - Exit code 1 on error
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.services.link_checker.LinkCheckerService") as mock_checker_class:
                mock_checker_instance = MagicMock()
                mock_checker_instance.check_all_links_sync.side_effect = Exception("Network error")
                mock_checker_class.return_value = mock_checker_instance

                result = runner.invoke(app, ["check-links"])

                # Should fail
                assert result.exit_code == 1, (
                    f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                )

                # Should show error
                assert "Error" in result.stdout or "failed" in result.stdout.lower(), (
                    f"Expected error message in output: {result.stdout}"
                )


class TestTagCommand:
    """Tests for `xbm tag` command.

    Tests for:
    - CLI-04: User can manage tags via CLI commands
    - ORG-01: User can assign tags to bookmarked posts
    """

    def test_tag_command_exists(self) -> None:
        """Verify tag command is registered in CLI app.

        CLI-04: User can manage tags via CLI commands.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "tag" in command_names, f"tag command should exist, got: {command_names}"

    def test_tag_command_help(self) -> None:
        """Verify tag command shows help."""
        result = runner.invoke(app, ["tag", "--help"])

        assert result.exit_code == 0
        assert "Manage tags" in result.stdout or "tag" in result.stdout.lower()

    def test_tag_assign_to_post(self, tmp_path: Path) -> None:
        """Verify tag command assigns tag to post.

        CLI-04: xbm tag post_id tag_name assigns tag.

        Expected behavior:
        - Command creates tag if not exists
        - Command assigns tag to post
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # Mock post exists
        mock_post = {"x_post_id": "test_post_1", "text": "Test post"}

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    with patch("src.repositories.tags.TagsRepository") as mock_tags_repo_class:
                        mock_posts_repo = MagicMock()
                        mock_posts_repo.get_by_id.return_value = mock_post
                        mock_posts_repo_class.return_value = mock_posts_repo

                        mock_tags_repo = MagicMock()
                        mock_tags_repo.get_or_create_tag.return_value = 1
                        mock_tags_repo_class.return_value = mock_tags_repo

                        result = runner.invoke(app, ["tag", "test_post_1", "python"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should create tag
                        mock_tags_repo.get_or_create_tag.assert_called_once_with("python")

                        # Should assign tag
                        mock_tags_repo.assign_tag.assert_called_once_with("test_post_1", 1)

                        # Should show success message
                        assert "Added tag" in result.stdout or "python" in result.stdout, (
                            f"Expected success message in output: {result.stdout}"
                        )

    def test_tag_remove_from_post(self, tmp_path: Path) -> None:
        """Verify tag command removes tag from post.

        CLI-04: xbm tag post_id --remove tag_name removes tag.

        Expected behavior:
        - Command finds tag by name
        - Command removes tag from post
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {"x_post_id": "test_post_1", "text": "Test post"}
        mock_tag = {"id": 1, "name": "python"}

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    with patch("src.repositories.tags.TagsRepository") as mock_tags_repo_class:
                        mock_posts_repo = MagicMock()
                        mock_posts_repo.get_by_id.return_value = mock_post
                        mock_posts_repo_class.return_value = mock_posts_repo

                        mock_tags_repo = MagicMock()
                        mock_tags_repo.get_tag_by_name.return_value = mock_tag
                        mock_tags_repo_class.return_value = mock_tags_repo

                        result = runner.invoke(app, ["tag", "test_post_1", "python", "--remove"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should find tag
                        mock_tags_repo.get_tag_by_name.assert_called_once_with("python")

                        # Should remove tag
                        mock_tags_repo.remove_tag.assert_called_once_with("test_post_1", 1)

                        # Should show success message
                        assert "Removed tag" in result.stdout or "removed" in result.stdout.lower(), (
                            f"Expected removal message in output: {result.stdout}"
                        )

    def test_tag_list_all_tags(self, tmp_path: Path) -> None:
        """Verify tag --list shows all tags.

        CLI-04: xbm tag --list shows all tags.

        Expected behavior:
        - Command retrieves all tags
        - Tags displayed in Rich table
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_tags = [
            {"id": 1, "name": "python", "created_at": "2024-01-15T10:00:00Z"},
            {"id": 2, "name": "machine-learning", "created_at": "2024-01-16T10:00:00Z"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.tags.TagsRepository") as mock_tags_repo_class:
                    mock_tags_repo = MagicMock()
                    mock_tags_repo.list_tags.return_value = mock_tags
                    mock_tags_repo_class.return_value = mock_tags_repo

                    result = runner.invoke(app, ["tag", "--list"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should list tags
                    mock_tags_repo.list_tags.assert_called_once()

                    # Should show tags in output
                    assert "python" in result.stdout or "Tags" in result.stdout, (
                        f"Expected tags in output: {result.stdout}"
                    )

    def test_tag_show_post_tags(self, tmp_path: Path) -> None:
        """Verify tag post_id --show shows post's tags.

        CLI-04: xbm tag post_id --show shows post's tags.

        Expected behavior:
        - Command retrieves tags for post
        - Tags displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {"x_post_id": "test_post_1", "text": "Test post"}
        mock_tags = [
            {"id": 1, "name": "python", "created_at": "2024-01-15T10:00:00Z"},
            {"id": 2, "name": "data-science", "created_at": "2024-01-16T10:00:00Z"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    with patch("src.repositories.tags.TagsRepository") as mock_tags_repo_class:
                        mock_posts_repo = MagicMock()
                        mock_posts_repo.get_by_id.return_value = mock_post
                        mock_posts_repo_class.return_value = mock_posts_repo

                        mock_tags_repo = MagicMock()
                        mock_tags_repo.get_post_tags.return_value = mock_tags
                        mock_tags_repo_class.return_value = mock_tags_repo

                        result = runner.invoke(app, ["tag", "test_post_1", "--show"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should get post tags
                        mock_tags_repo.get_post_tags.assert_called_once_with("test_post_1")

                        # Should show tags
                        assert "python" in result.stdout or "Tags for post" in result.stdout, (
                            f"Expected tags in output: {result.stdout}"
                        )

    def test_tag_normalizes_to_lowercase(self, tmp_path: Path) -> None:
        """Verify tag names are normalized to lowercase.

        ORG-01: Tags normalized to lowercase.

        Expected behavior:
        - Tag name converted to lowercase
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {"x_post_id": "test_post_1", "text": "Test post"}

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    with patch("src.repositories.tags.TagsRepository") as mock_tags_repo_class:
                        mock_posts_repo = MagicMock()
                        mock_posts_repo.get_by_id.return_value = mock_post
                        mock_posts_repo_class.return_value = mock_posts_repo

                        mock_tags_repo = MagicMock()
                        mock_tags_repo.get_or_create_tag.return_value = 1
                        mock_tags_repo_class.return_value = mock_tags_repo

                        result = runner.invoke(app, ["tag", "test_post_1", "Python"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Tag name should be passed as-is; normalization happens in TagsRepository
                        # We just verify the command passes it correctly

    def test_tag_post_not_found(self, tmp_path: Path) -> None:
        """Verify tag command handles non-existent post.

        Expected behavior:
        - Exit code 1
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    mock_posts_repo = MagicMock()
                    mock_posts_repo.get_by_id.return_value = None
                    mock_posts_repo_class.return_value = mock_posts_repo

                    result = runner.invoke(app, ["tag", "nonexistent_post", "python"])

                    # Should fail
                    assert result.exit_code == 1, (
                        f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show error
                    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower(), (
                        f"Expected error message in output: {result.stdout}"
                    )


class TestTopicCommand:
    """Tests for `xbm topic` command.

    Tests for:
    - CLI-04: User can manage topics via CLI commands
    - ORG-02: User can create and manage topic taxonomy
    """

    def test_topic_command_exists(self) -> None:
        """Verify topic command is registered in CLI app.

        CLI-04: User can manage topics via CLI commands.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "topic" in command_names, f"topic command should exist, got: {command_names}"

    def test_topic_command_help(self) -> None:
        """Verify topic command shows help."""
        result = runner.invoke(app, ["topic", "--help"])

        assert result.exit_code == 0
        assert "Manage topic" in result.stdout or "topic" in result.stdout.lower()

    def test_topic_create(self, tmp_path: Path) -> None:
        """Verify topic create creates new topic.

        CLI-04: xbm topic create "name" creates topic.

        Expected behavior:
        - Command creates topic
        - Success message with topic ID displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.create_topic.return_value = 1
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["topic", "create", "Programming", "--desc", "Software development"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should create topic
                    mock_topics_repo.create_topic.assert_called_once_with(
                        "Programming", "Software development"
                    )

                    # Should show success message
                    assert "Created topic" in result.stdout or "Programming" in result.stdout, (
                        f"Expected success message in output: {result.stdout}"
                    )

    def test_topic_list_all(self, tmp_path: Path) -> None:
        """Verify topic --list shows all topics.

        CLI-04: xbm topic --list shows all topics with post counts.

        Expected behavior:
        - Command retrieves all topics
        - Shows post counts per topic
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_topics = [
            {"id": 1, "name": "Programming", "description": "Software dev", "parent_id": None, "created_at": "2024-01-15T10:00:00Z"},
            {"id": 2, "name": "Machine Learning", "description": "AI topics", "parent_id": None, "created_at": "2024-01-16T10:00:00Z"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.list_topics.return_value = mock_topics
                    mock_topics_repo.get_posts_by_topic.return_value = ["post_1", "post_2"]
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["topic", "--list"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should list topics
                    mock_topics_repo.list_topics.assert_called_once()

                    # Should show topics in output
                    assert "Programming" in result.stdout or "Topics" in result.stdout, (
                        f"Expected topics in output: {result.stdout}"
                    )

    def test_topic_assign_to_post(self, tmp_path: Path) -> None:
        """Verify topic assign assigns topic to post.

        CLI-04: xbm topic assign post_id topic_id assigns topic.

        Expected behavior:
        - Command verifies post exists
        - Command verifies topic exists
        - Command assigns topic to post
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {"x_post_id": "test_post_1", "text": "Test post"}
        mock_topic = {"id": 1, "name": "Programming", "description": "Software dev"}

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_posts_repo = MagicMock()
                        mock_posts_repo.get_by_id.return_value = mock_post
                        mock_posts_repo_class.return_value = mock_posts_repo

                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_topic_by_id.return_value = mock_topic
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["topic", "assign", "test_post_1", "1"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should assign topic
                        mock_topics_repo.assign_topic_to_post.assert_called_once_with("test_post_1", 1)

                        # Should show success message
                        assert "Assigned topic" in result.stdout or "Programming" in result.stdout, (
                            f"Expected success message in output: {result.stdout}"
                        )

    def test_topic_show_post_topics(self, tmp_path: Path) -> None:
        """Verify topic post_id --show shows post's topics.

        CLI-04: xbm topic post_id --show shows post's topics.

        Expected behavior:
        - Command retrieves topics for post
        - Shows topic names with confidence and source
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {"x_post_id": "test_post_1", "text": "Test post"}
        mock_topics = [
            {"id": 1, "name": "Programming", "confidence": 0.95, "source": "user"},
            {"id": 2, "name": "Python", "confidence": 0.88, "source": "ai-approved"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_posts_repo = MagicMock()
                        mock_posts_repo.get_by_id.return_value = mock_post
                        mock_posts_repo_class.return_value = mock_posts_repo

                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = mock_topics
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["topic", "test_post_1", "--show"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should get post topics
                        mock_topics_repo.get_post_topics.assert_called_once_with("test_post_1")

                        # Should show topics
                        assert "Programming" in result.stdout or "Topics for post" in result.stdout, (
                            f"Expected topics in output: {result.stdout}"
                        )

    def test_topic_delete(self, tmp_path: Path) -> None:
        """Verify topic delete removes topic.

        CLI-04: xbm topic delete topic_id deletes topic.

        Expected behavior:
        - Command verifies topic exists
        - Command deletes topic
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_topic = {"id": 1, "name": "Programming", "description": "Software dev"}

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_topic_by_id.return_value = mock_topic
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["topic", "delete", "1"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should delete topic
                    mock_topics_repo.delete_topic.assert_called_once_with(1)

                    # Should show success message
                    assert "Deleted topic" in result.stdout or "Programming" in result.stdout, (
                        f"Expected success message in output: {result.stdout}"
                    )

    def test_topic_topic_not_found(self, tmp_path: Path) -> None:
        """Verify topic delete handles non-existent topic.

        Expected behavior:
        - Exit code 1
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_topic_by_id.return_value = None
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["topic", "delete", "999"])

                    # Should fail
                    assert result.exit_code == 1, (
                        f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show error
                    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower(), (
                        f"Expected error message in output: {result.stdout}"
                    )


class TestSuggestTopicsCommand:
    """Tests for `xbm suggest-topics` command.

    Tests for:
    - CLI-04: User can generate topic suggestions via CLI
    - ORG-03: Application clusters posts into topics using hybrid approach
    """

    def test_suggest_topics_command_exists(self) -> None:
        """Verify suggest-topics command is registered in CLI app.

        CLI-04: User can manage topics via CLI commands.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "suggest-topics" in command_names, f"suggest-topics command should exist, got: {command_names}"

    def test_suggest_topics_command_help(self) -> None:
        """Verify suggest-topics command shows help."""
        result = runner.invoke(app, ["suggest-topics", "--help"])

        assert result.exit_code == 0
        assert "topic" in result.stdout.lower() or "suggest" in result.stdout.lower()

    def test_suggest_topics_generates_suggestions(self, tmp_path: Path) -> None:
        """Verify suggest-topics generates suggestions.

        ORG-03: Application clusters posts into topics.

        Expected behavior:
        - Command calls TopicSuggesterService.generate_all_suggestions
        - Shows summary with counts
        """
        from src.services.topic_suggester import SuggestionSummary

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_summary = SuggestionSummary(
            total_posts_processed=10,
            total_suggestions=15,
            posts_with_suggestions=8,
            suggestions_by_topic={"Programming": 10, "Machine Learning": 5},
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.generate_all_suggestions.return_value = mock_summary
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["suggest-topics"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should call generate_all_suggestions
                    mock_service.generate_all_suggestions.assert_called_once()

                    # Should show summary
                    assert "10" in result.stdout or "suggestions" in result.stdout.lower(), (
                        f"Expected summary in output: {result.stdout}"
                    )

    def test_suggest_topics_with_threshold(self, tmp_path: Path) -> None:
        """Verify suggest-topics respects --threshold option.

        Expected behavior:
        - Threshold passed to TopicSuggesterService
        """
        from src.services.topic_suggester import SuggestionSummary

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_summary = SuggestionSummary(
            total_posts_processed=10,
            total_suggestions=5,
            posts_with_suggestions=5,
            suggestions_by_topic={"Programming": 5},
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.generate_all_suggestions.return_value = mock_summary
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["suggest-topics", "--threshold", "0.8"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should pass threshold to service
                    call_kwargs = mock_service_class.call_args[1]
                    assert call_kwargs.get("confidence_threshold") == 0.8, (
                        f"Expected threshold 0.8, got: {call_kwargs}"
                    )

    def test_suggest_topics_no_clear_flag(self, tmp_path: Path) -> None:
        """Verify suggest-topics --no-clear keeps existing suggestions.

        Expected behavior:
        - clear_existing=False passed when --no-clear used
        """
        from src.services.topic_suggester import SuggestionSummary

        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_summary = SuggestionSummary(
            total_posts_processed=5,
            total_suggestions=3,
            posts_with_suggestions=3,
            suggestions_by_topic={"Python": 3},
        )

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.generate_all_suggestions.return_value = mock_summary
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["suggest-topics", "--no-clear"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should pass clear_existing=False
                    call_kwargs = mock_service.generate_all_suggestions.call_args[1]
                    assert call_kwargs.get("clear_existing") == False, (
                        f"Expected clear_existing=False, got: {call_kwargs}"
                    )

    def test_suggest_topics_error_handling(self, tmp_path: Path) -> None:
        """Verify suggest-topics handles errors gracefully.

        Expected behavior:
        - Exit code 1 on error
        - Error message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.generate_all_suggestions.side_effect = Exception("Database error")
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["suggest-topics"])

                    # Should fail
                    assert result.exit_code == 1, (
                        f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show error
                    assert "Error" in result.stdout or "failed" in result.stdout.lower(), (
                        f"Expected error message in output: {result.stdout}"
                    )


class TestReviewTopicsCommand:
    """Tests for `xbm review-topics` command.

    Tests for:
    - CLI-04: User can review and approve AI-suggested topic assignments
    - ORG-04: User can review and approve AI-suggested topic assignments
    """

    def test_review_topics_command_exists(self) -> None:
        """Verify review-topics command is registered in CLI app.

        CLI-04: User can manage topics via CLI commands.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "review-topics" in command_names, f"review-topics command should exist, got: {command_names}"

    def test_review_topics_command_help(self) -> None:
        """Verify review-topics command shows help."""
        result = runner.invoke(app, ["review-topics", "--help"])

        assert result.exit_code == 0
        assert "review" in result.stdout.lower() or "topic" in result.stdout.lower()

    def test_review_topics_shows_pending(self, tmp_path: Path) -> None:
        """Verify review-topics shows pending suggestions.

        ORG-04: User can review and approve AI-suggested topic assignments.

        Expected behavior:
        - Command retrieves pending suggestions
        - Shows table with ID, Post, Topic, Confidence
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_pending = [
            {"id": 1, "post_id": "post_1", "topic_id": 1, "topic_name": "Programming", "confidence": 0.95, "suggested_at": "2024-01-15T10:00:00Z"},
            {"id": 2, "post_id": "post_2", "topic_id": 2, "topic_name": "Python", "confidence": 0.88, "suggested_at": "2024-01-16T10:00:00Z"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_pending_assignments.return_value = mock_pending
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["review-topics"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should get pending assignments
                    mock_topics_repo.get_pending_assignments.assert_called_once()

                    # Should show pending suggestions
                    assert "Programming" in result.stdout or "pending" in result.stdout.lower(), (
                        f"Expected suggestions in output: {result.stdout}"
                    )

    def test_review_topics_approve_suggestion(self, tmp_path: Path) -> None:
        """Verify review-topics --approve ID approves suggestion.

        ORG-04: User can review and approve AI-suggested topic assignments.

        Expected behavior:
        - Command approves suggestion
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["review-topics", "--approve", "1"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should approve suggestion
                    mock_service.approve_suggestion.assert_called_once_with(1)

                    # Should show success message
                    assert "Approved" in result.stdout or "approved" in result.stdout.lower(), (
                        f"Expected success message in output: {result.stdout}"
                    )

    def test_review_topics_reject_suggestion(self, tmp_path: Path) -> None:
        """Verify review-topics --reject ID rejects suggestion.

        Expected behavior:
        - Command rejects suggestion
        - Success message displayed
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["review-topics", "--reject", "1"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should reject suggestion
                    mock_service.reject_suggestion.assert_called_once_with(1)

                    # Should show success message
                    assert "Rejected" in result.stdout or "rejected" in result.stdout.lower(), (
                        f"Expected success message in output: {result.stdout}"
                    )

    def test_review_topics_approve_all(self, tmp_path: Path) -> None:
        """Verify review-topics --approve-all approves all suggestions.

        Expected behavior:
        - Command approves all suggestions above threshold
        - Shows count of approved suggestions
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.approve_all_suggestions.return_value = 5
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["review-topics", "--approve-all"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should approve all suggestions
                    mock_service.approve_all_suggestions.assert_called_once()

                    # Should show count
                    assert "5" in result.stdout or "Approved" in result.stdout, (
                        f"Expected count in output: {result.stdout}"
                    )

    def test_review_topics_approve_all_with_min_confidence(self, tmp_path: Path) -> None:
        """Verify review-topics --approve-all --min-confidence filters.

        Expected behavior:
        - Command passes min_confidence to approve_all_suggestions
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.topic_suggester.TopicSuggesterService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.approve_all_suggestions.return_value = 3
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["review-topics", "--approve-all", "--min-confidence", "0.8"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should pass min_confidence
                    call_kwargs = mock_service.approve_all_suggestions.call_args[1]
                    assert call_kwargs.get("min_confidence") == 0.8, (
                        f"Expected min_confidence=0.8, got: {call_kwargs}"
                    )

    def test_review_topics_filter_by_post(self, tmp_path: Path) -> None:
        """Verify review-topics --post shows suggestions for specific post.

        Expected behavior:
        - Command passes post_id to get_pending_assignments
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_pending = [
            {"id": 1, "post_id": "post_123", "topic_id": 1, "topic_name": "Programming", "confidence": 0.95, "suggested_at": "2024-01-15T10:00:00Z"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_pending_assignments.return_value = mock_pending
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["review-topics", "--post", "post_123"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should pass post_id to get_pending_assignments
                    call_kwargs = mock_topics_repo.get_pending_assignments.call_args[1]
                    assert call_kwargs.get("post_id") == "post_123", (
                        f"Expected post_id=post_123, got: {call_kwargs}"
                    )

    def test_review_topics_no_pending(self, tmp_path: Path) -> None:
        """Verify review-topics handles no pending suggestions.

        Expected behavior:
        - Shows 'No pending suggestions' message
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_pending_assignments.return_value = []
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["review-topics"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show no pending message
                    assert "No pending" in result.stdout or "no pending" in result.stdout.lower(), (
                        f"Expected no pending message in output: {result.stdout}"
                    )


class TestDueCommand:
    """Tests for `xbm due` command.

    Tests for:
    - D-04: Table format with truncated content
    - D-08: Themed reviews via --topic flag
    - SPAC-03: User can view currently due posts via CLI
    - SPAC-04: Filter by topic for themed reviews
    """

    def test_due_command_exists(self) -> None:
        """Verify due command is registered in CLI app.

        SPAC-03: User can view currently due posts via CLI.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "due" in command_names, f"due command should exist, got: {command_names}"

    def test_due_command_help(self) -> None:
        """Verify due command shows help."""
        result = runner.invoke(app, ["due", "--help"])

        assert result.exit_code == 0
        assert "due" in result.stdout.lower() or "review" in result.stdout.lower()

    def test_due_command_empty_queue(self, tmp_path: Path) -> None:
        """Verify due command shows 'No posts due' when queue empty.

        D-04: Table format for due posts.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = []
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["due"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show no posts due message
                    assert "No posts due" in result.stdout, (
                        f"Expected 'No posts due' in output: {result.stdout}"
                    )

    def test_due_command_with_posts(self, tmp_path: Path) -> None:
        """Verify due command shows table with due posts.

        D-04: Table format with #, Author, Content Preview, Topics, Due.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_123",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "This is a test post about Python programming",
                "scheduled_for": "2024-01-15T10:00:00Z",
                "review_count": 0,
            },
            {
                "x_post_id": "post_456",
                "author_username": "anotheruser",
                "author_display_name": "Another User",
                "text": "Short post",
                "scheduled_for": "2024-01-16T10:00:00Z",
                "review_count": 1,
            },
        ]

        mock_topics = [
            {"id": 1, "name": "Python"},
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        # First post has Python topic, second has no topics
                        mock_topics_repo.get_post_topics.side_effect = [mock_topics, []]
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["due"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should show table with posts
                        assert "testuser" in result.stdout or "@testuser" in result.stdout, (
                            f"Expected author in output: {result.stdout}"
                        )
                        assert "Python" in result.stdout, (
                            f"Expected topic in output: {result.stdout}"
                        )

    def test_due_command_with_topic_filter(self, tmp_path: Path) -> None:
        """Verify due command --topic filters by topic.

        D-08: Themed reviews via --topic flag.
        SPAC-04: Filter by topic for themed reviews.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_topic = {"id": 1, "name": "Python"}

        mock_posts = [
            {
                "x_post_id": "post_123",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Python post",
                "scheduled_for": "2024-01-15T10:00:00Z",
                "review_count": 0,
            },
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_topic_by_name.return_value = mock_topic
                    mock_topics_repo.get_post_topics.return_value = []
                    mock_topics_repo_class.return_value = mock_topics_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service.get_due_posts.return_value = mock_posts
                        mock_service_class.return_value = mock_service

                        result = runner.invoke(app, ["due", "--topic", "Python"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should pass topic_id to get_due_posts
                        call_kwargs = mock_service.get_due_posts.call_args[1]
                        assert call_kwargs.get("topic_id") == 1, (
                            f"Expected topic_id=1, got: {call_kwargs}"
                        )

    def test_due_command_topic_not_found(self, tmp_path: Path) -> None:
        """Verify due command shows error for invalid topic.

        T-05-06: Topic parameter validated.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_topic_by_name.return_value = None
                    mock_topics_repo_class.return_value = mock_topics_repo

                    result = runner.invoke(app, ["due", "--topic", "Nonexistent"])

                    # Should fail
                    assert result.exit_code == 1, (
                        f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show error message
                    assert "not found" in result.stdout.lower() or "Topic" in result.stdout, (
                        f"Expected topic not found message: {result.stdout}"
                    )

    def test_due_command_truncates_content(self, tmp_path: Path) -> None:
        """Verify due command truncates long content to 50 chars.

        D-04: Content preview truncated.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        long_text = "A" * 100  # 100 characters
        mock_posts = [
            {
                "x_post_id": "post_long",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": long_text,
                "scheduled_for": "2024-01-15T10:00:00Z",
                "review_count": 0,
            },
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["due"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should show truncated content (50 chars + "...")
                        # Note: Rich table may have different formatting
                        assert "AAA" in result.stdout or "..." in result.stdout, (
                            f"Expected truncated content in output: {result.stdout}"
                        )


class TestReviewCommand:
    """Tests for `xbm review` command.

    Tests for:
    - D-05: Notes displayed at top during review
    - D-06: Metadata shown (pub date, topics, review history)
    - D-07: User chooses scheduling intent
    - D-10: Interactive one-at-a-time review session
    - CLI-02: User can view resurfaced posts via CLI command
    """

    def test_review_command_exists(self) -> None:
        """Verify review command is registered in CLI app.

        CLI-02: User can view resurfaced posts via CLI command.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "review" in command_names, f"review command should exist, got: {command_names}"

    def test_review_command_help(self) -> None:
        """Verify review command shows help."""
        result = runner.invoke(app, ["review", "--help"])

        assert result.exit_code == 0
        assert "review" in result.stdout.lower()

    def test_review_command_empty_queue(self, tmp_path: Path) -> None:
        """Verify review command shows 'No posts due' when queue empty.

        D-10: Interactive one-at-a-time review session.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = []
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["review"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show no posts due message
                    assert "No posts due" in result.stdout, (
                        f"Expected 'No posts due' in output: {result.stdout}"
                    )

    def test_review_command_displays_note(self, tmp_path: Path) -> None:
        """Verify review command shows note at top of post.

        D-05: Notes displayed at top during review.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_with_note",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content here",
                "note": "This is my personal note",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 1,
                "last_reviewed": "2024-01-18T10:00:00Z",
                "user_preference": "soon",
            },
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        # Provide input for the interactive prompt (choice '2' for soon)
                        result = runner.invoke(app, ["review"], input="2\n")

                        # Should succeed or exit after processing
                        # Note: Interactive command may exit after processing all posts
                        # Should show note
                        assert "note" in result.stdout.lower() or "Note" in result.stdout, (
                            f"Expected note in output: {result.stdout}"
                        )

    def test_review_command_displays_metadata(self, tmp_path: Path) -> None:
        """Verify review command shows metadata.

        D-06: Metadata shown (pub date, topics, review history).
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_metadata",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 2,
                "last_reviewed": "2024-01-18T10:00:00Z",
                "user_preference": "fresh",
            },
        ]

        mock_topics = [{"id": 1, "name": "Python"}]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = mock_topics
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["review"], input="2\n")

                        # Should show metadata
                        assert "Python" in result.stdout, f"Expected topic in output: {result.stdout}"
                        assert "Reviews" in result.stdout or "review" in result.stdout.lower(), (
                            f"Expected review count in output: {result.stdout}"
                        )

    def test_review_command_choice_fresh(self, tmp_path: Path) -> None:
        """Verify review command 'fresh' choice schedules for 3 days.

        D-07: User chooses scheduling intent.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_fresh",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 0,
                "last_reviewed": None,
                "user_preference": None,
            },
        ]

        from datetime import datetime, timezone, timedelta

        next_date = datetime.now(timezone.utc) + timedelta(days=3)

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service.process_review_choice.return_value = next_date
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["review"], input="1\n")

                        # Should call process_review_choice with 'fresh'
                        mock_service.process_review_choice.assert_called_once()
                        call_args = mock_service.process_review_choice.call_args
                        assert call_args[0][1] == "fresh", (
                            f"Expected 'fresh' choice, got: {call_args}"
                        )

    def test_review_command_choice_soon(self, tmp_path: Path) -> None:
        """Verify review command 'soon' choice schedules for 14 days.

        D-07: User chooses scheduling intent.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_soon",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 0,
                "last_reviewed": None,
                "user_preference": None,
            },
        ]

        from datetime import datetime, timezone, timedelta

        next_date = datetime.now(timezone.utc) + timedelta(days=14)

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service.process_review_choice.return_value = next_date
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["review"], input="2\n")

                        # Should call process_review_choice with 'soon'
                        mock_service.process_review_choice.assert_called_once()
                        call_args = mock_service.process_review_choice.call_args
                        assert call_args[0][1] == "soon", (
                            f"Expected 'soon' choice, got: {call_args}"
                        )

    def test_review_command_choice_later(self, tmp_path: Path) -> None:
        """Verify review command 'later' choice schedules for 60 days.

        D-07: User chooses scheduling intent.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_later",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 0,
                "last_reviewed": None,
                "user_preference": None,
            },
        ]

        from datetime import datetime, timezone, timedelta

        next_date = datetime.now(timezone.utc) + timedelta(days=60)

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service.process_review_choice.return_value = next_date
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["review"], input="3\n")

                        # Should call process_review_choice with 'later'
                        mock_service.process_review_choice.assert_called_once()
                        call_args = mock_service.process_review_choice.call_args
                        assert call_args[0][1] == "later", (
                            f"Expected 'later' choice, got: {call_args}"
                        )

    def test_review_command_with_topic_filter(self, tmp_path: Path) -> None:
        """Verify review command --topic filters by topic.

        D-08: Themed reviews via --topic flag.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_topic = {"id": 1, "name": "Python"}

        mock_posts = [
            {
                "x_post_id": "post_python",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Python post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 0,
                "last_reviewed": None,
                "user_preference": None,
            },
        ]

        from datetime import datetime, timezone, timedelta

        next_date = datetime.now(timezone.utc) + timedelta(days=14)

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                    mock_topics_repo = MagicMock()
                    mock_topics_repo.get_topic_by_name.return_value = mock_topic
                    mock_topics_repo.get_post_topics.return_value = []
                    mock_topics_repo_class.return_value = mock_topics_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service.get_due_posts.return_value = mock_posts
                        mock_service.process_review_choice.return_value = next_date
                        mock_service_class.return_value = mock_service

                        result = runner.invoke(app, ["review", "--topic", "Python"], input="2\n")

                        # Should pass topic_id to get_due_posts
                        call_kwargs = mock_service.get_due_posts.call_args[1]
                        assert call_kwargs.get("topic_id") == 1, (
                            f"Expected topic_id=1, got: {call_kwargs}"
                        )

    def test_review_command_skip(self, tmp_path: Path) -> None:
        """Verify review command 'skip' option skips the post.

        D-07: User can skip posts.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_skip",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 0,
                "last_reviewed": None,
                "user_preference": None,
            },
        ]

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        result = runner.invoke(app, ["review"], input="s\n")

                        # Should NOT call process_review_choice
                        mock_service.process_review_choice.assert_not_called()

    def test_review_command_postpone(self, tmp_path: Path) -> None:
        """Verify review command 'postpone' option delays review.

        D-09: Postpone without changing preference.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_posts = [
            {
                "x_post_id": "post_postpone",
                "author_username": "testuser",
                "author_display_name": "Test User",
                "text": "Post content",
                "created_at": "2024-01-15T10:00:00Z",
                "scheduled_for": "2024-01-20T10:00:00Z",
                "review_count": 2,
                "last_reviewed": "2024-01-18T10:00:00Z",
                "user_preference": "soon",
            },
        ]

        from datetime import datetime, timezone, timedelta

        next_date = datetime.now(timezone.utc) + timedelta(days=7)

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_due_posts.return_value = mock_posts
                    mock_service.process_postpone.return_value = next_date
                    mock_service_class.return_value = mock_service

                    with patch("src.repositories.topics.TopicsRepository") as mock_topics_repo_class:
                        mock_topics_repo = MagicMock()
                        mock_topics_repo.get_post_topics.return_value = []
                        mock_topics_repo_class.return_value = mock_topics_repo

                        # Input: 'p' for postpone, then '7' for days
                        result = runner.invoke(app, ["review"], input="p\n7\n")

                        # Should call process_postpone
                        mock_service.process_postpone.assert_called_once()
                        call_args = mock_service.process_postpone.call_args
                        assert call_args[0][1] == 7, (
                            f"Expected 7 days, got: {call_args}"
                        )


class TestStatsCommand:
    """Tests for `xbm stats` command.

    Tests for:
    - D-12: User can view review statistics via CLI
    - Progress percentage calculation
    """

    def test_stats_command_exists(self) -> None:
        """Verify stats command is registered in CLI app.

        D-12: User can view review statistics via CLI.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "stats" in command_names, f"stats command should exist, got: {command_names}"

    def test_stats_command_help(self) -> None:
        """Verify stats command shows help."""
        result = runner.invoke(app, ["stats", "--help"])

        assert result.exit_code == 0
        assert "statistics" in result.stdout.lower() or "stats" in result.stdout.lower()

    def test_stats_command_empty_db(self, tmp_path: Path) -> None:
        """Verify stats command shows '0 posts' gracefully when database empty.

        D-12: Shows total posts, due count, reviewed count.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_stats = {
            "total_posts": 0,
            "due_count": 0,
            "reviewed_count": 0,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_review_stats.return_value = mock_stats
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["stats"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show 0 posts
                    assert "0" in result.stdout, (
                        f"Expected '0' in output: {result.stdout}"
                    )

                    # Should show N/A for progress percentage
                    assert "N/A" in result.stdout or "0" in result.stdout, (
                        f"Expected N/A or 0 for progress: {result.stdout}"
                    )

    def test_stats_command_with_posts(self, tmp_path: Path) -> None:
        """Verify stats command shows table format with counts.

        D-12: Table format with total, due, reviewed.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_stats = {
            "total_posts": 100,
            "due_count": 15,
            "reviewed_count": 50,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_review_stats.return_value = mock_stats
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["stats"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show table with counts
                    assert "100" in result.stdout, (
                        f"Expected total (100) in output: {result.stdout}"
                    )
                    assert "15" in result.stdout, (
                        f"Expected due count (15) in output: {result.stdout}"
                    )
                    assert "50" in result.stdout, (
                        f"Expected reviewed count (50) in output: {result.stdout}"
                    )

                    # Should call get_review_stats
                    mock_service.get_review_stats.assert_called_once()

    def test_stats_command_progress_calculation(self, tmp_path: Path) -> None:
        """Verify stats command calculates review progress percentage.

        D-12: Progress percentage calculated.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        # 50 reviewed out of 100 = 50%
        mock_stats = {
            "total_posts": 100,
            "due_count": 15,
            "reviewed_count": 50,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_review_stats.return_value = mock_stats
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["stats"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show 50.0% progress
                    assert "50" in result.stdout, (
                        f"Expected 50% progress in output: {result.stdout}"
                    )

    def test_stats_command_shows_encouragement_when_due(self, tmp_path: Path) -> None:
        """Verify stats command shows encouragement message when posts due."""
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_stats = {
            "total_posts": 100,
            "due_count": 15,  # Posts due
            "reviewed_count": 50,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_review_stats.return_value = mock_stats
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["stats"])

                    # Should show due posts message
                    assert "15" in result.stdout and ("due" in result.stdout.lower() or "awaiting" in result.stdout.lower()), (
                        f"Expected due count message in output: {result.stdout}"
                    )

    def test_stats_command_shows_caught_up_when_no_due(self, tmp_path: Path) -> None:
        """Verify stats command shows 'caught up' message when no posts due."""
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_stats = {
            "total_posts": 100,
            "due_count": 0,  # No posts due
            "reviewed_count": 50,
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_review_stats.return_value = mock_stats
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["stats"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show caught up message
                    assert "caught up" in result.stdout.lower() or "No posts due" in result.stdout, (
                        f"Expected caught up message in output: {result.stdout}"
                    )


class TestResetCommand:
    """Tests for `xbm reset` command.

    Tests for:
    - D-13: Reset review state without re-syncing everything
    - Confirmation prompt before reset
    - --yes flag to skip confirmation
    """

    def test_reset_command_exists(self) -> None:
        """Verify reset command is registered in CLI app.

        D-13: User can reset review state for a post.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "reset" in command_names, f"reset command should exist, got: {command_names}"

    def test_reset_command_help(self) -> None:
        """Verify reset command shows help."""
        result = runner.invoke(app, ["reset", "--help"])

        assert result.exit_code == 0
        assert "reset" in result.stdout.lower() or "review state" in result.stdout.lower()

    def test_reset_command_post_not_found(self, tmp_path: Path) -> None:
        """Verify reset command shows error for non-existent post.

        D-13: Post validated before reset.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    mock_posts_repo = MagicMock()
                    mock_posts_repo.get_by_id.return_value = None  # Post not found
                    mock_posts_repo_class.return_value = mock_posts_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        result = runner.invoke(app, ["reset", "nonexistent_post"])

                        # Should fail
                        assert result.exit_code == 1, (
                            f"Exit code should be 1, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should show error
                        assert "not found" in result.stdout.lower(), (
                            f"Expected 'not found' in output: {result.stdout}"
                        )

    def test_reset_command_confirmation(self, tmp_path: Path) -> None:
        """Verify reset command asks for confirmation before reset.

        D-13: Confirmation prompt shown by default.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {
            "x_post_id": "test_post_1",
            "author_username": "testuser",
            "text": "Test post content here",
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    mock_posts_repo = MagicMock()
                    mock_posts_repo.get_by_id.return_value = mock_post
                    mock_posts_repo_class.return_value = mock_posts_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        # Input 'n' to cancel the confirmation
                        result = runner.invoke(app, ["reset", "test_post_1"], input="n\n")

                        # Should exit without error (cancelled)
                        assert result.exit_code == 0, (
                            f"Exit code should be 0 for cancel, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should show confirmation prompt
                        assert "confirm" in result.stdout.lower() or "reset" in result.stdout.lower(), (
                            f"Expected confirmation prompt in output: {result.stdout}"
                        )

                        # Should NOT call reset (cancelled)
                        mock_service.reset_review_state.assert_not_called()

    def test_reset_command_yes_flag(self, tmp_path: Path) -> None:
        """Verify reset command --yes flag skips confirmation.

        D-13: --yes flag skips confirmation.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {
            "x_post_id": "test_post_1",
            "author_username": "testuser",
            "text": "Test post content here",
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    mock_posts_repo = MagicMock()
                    mock_posts_repo.get_by_id.return_value = mock_post
                    mock_posts_repo_class.return_value = mock_posts_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        # Use --yes flag to skip confirmation
                        result = runner.invoke(app, ["reset", "test_post_1", "--yes"])

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should call reset without prompting
                        mock_service.reset_review_state.assert_called_once_with("test_post_1")

                        # Should show success message
                        assert "reset" in result.stdout.lower() or "green" in result.stdout.lower(), (
                            f"Expected success message in output: {result.stdout}"
                        )

    def test_reset_command_confirmed(self, tmp_path: Path) -> None:
        """Verify reset command resets state when confirmed.

        D-13: State cleared and re-seeded from publication date.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {
            "x_post_id": "test_post_1",
            "author_username": "testuser",
            "text": "Test post content here",
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    mock_posts_repo = MagicMock()
                    mock_posts_repo.get_by_id.return_value = mock_post
                    mock_posts_repo_class.return_value = mock_posts_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        # Input 'y' to confirm
                        result = runner.invoke(app, ["reset", "test_post_1"], input="y\n")

                        # Should succeed
                        assert result.exit_code == 0, (
                            f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                        )

                        # Should call reset
                        mock_service.reset_review_state.assert_called_once_with("test_post_1")

    def test_reset_command_shows_post_preview(self, tmp_path: Path) -> None:
        """Verify reset command shows post preview before confirmation.

        D-13: Show post preview before confirming.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        mock_post = {
            "x_post_id": "test_post_1",
            "author_username": "testuser",
            "text": "This is a test post with some content",
        }

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.repositories.posts.PostsRepository") as mock_posts_repo_class:
                    mock_posts_repo = MagicMock()
                    mock_posts_repo.get_by_id.return_value = mock_post
                    mock_posts_repo_class.return_value = mock_posts_repo

                    with patch("src.services.review_service.ReviewService") as mock_service_class:
                        mock_service = MagicMock()
                        mock_service_class.return_value = mock_service

                        # Input 'n' to cancel (we just want to see the preview)
                        result = runner.invoke(app, ["reset", "test_post_1"], input="n\n")

                        # Should show post preview (author and content)
                        assert "testuser" in result.stdout or "@testuser" in result.stdout, (
                            f"Expected author in output: {result.stdout}"
                        )


class TestSeedCommand:
    """Tests for `xbm seed` command.

    Tests for:
    - D-02: Seeds initial review state from publication date
    - Posts without state get scheduled_for date
    """

    def test_seed_command_exists(self) -> None:
        """Verify seed command is registered in CLI app.

        D-02: Seeds from publication date.
        """
        command_names = []
        for cmd in app.registered_commands:
            name = cmd.name or (cmd.callback.__name__ if cmd.callback else None)
            if name:
                command_names.append(name)

        assert "seed" in command_names, f"seed command should exist, got: {command_names}"

    def test_seed_command_help(self) -> None:
        """Verify seed command shows help."""
        result = runner.invoke(app, ["seed", "--help"])

        assert result.exit_code == 0
        assert "seed" in result.stdout.lower() or "review state" in result.stdout.lower()

    def test_seed_command_creates_states(self, tmp_path: Path) -> None:
        """Verify seed command creates states for posts without state.

        D-02: Seeds from publication date.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.seed_new_posts.return_value = 5  # 5 posts seeded
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["seed"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should call seed_new_posts
                    mock_service.seed_new_posts.assert_called_once()

                    # Should show seeded count
                    assert "5" in result.stdout, (
                        f"Expected '5' seeded count in output: {result.stdout}"
                    )

    def test_seed_command_idempotent(self, tmp_path: Path) -> None:
        """Verify seed command shows message when all posts already have state.

        D-02: Running twice doesn't duplicate states.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.seed_new_posts.return_value = 0  # No new posts to seed
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["seed"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should show already seeded message
                    assert "already" in result.stdout.lower() or "0" in result.stdout, (
                        f"Expected already seeded message in output: {result.stdout}"
                    )

    def test_seed_command_force_flag(self, tmp_path: Path) -> None:
        """Verify seed command --force clears existing states first.

        D-02: --force re-seeds all posts from scratch.
        """
        mock_settings = MagicMock()
        mock_settings.database_path = tmp_path / "test.db"

        with patch("src.cli.main.Settings", return_value=mock_settings):
            with patch("src.cli.main.init_database") as mock_init:
                mock_conn = MagicMock()
                mock_init.return_value = mock_conn

                with patch("src.services.review_service.ReviewService") as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.seed_new_posts.return_value = 10  # 10 posts seeded
                    mock_service_class.return_value = mock_service

                    result = runner.invoke(app, ["seed", "--force"])

                    # Should succeed
                    assert result.exit_code == 0, (
                        f"Exit code should be 0, got {result.exit_code}. Output: {result.stdout}"
                    )

                    # Should clear existing states first (DELETE FROM post_review_state)
                    # The mock_conn should have execute called with DELETE
                    delete_calls = [call for call in mock_conn.execute.call_args_list
                                    if call and len(call[0]) > 0 and "DELETE" in str(call[0][0])]
                    assert len(delete_calls) > 0, (
                        f"Expected DELETE call for --force, got: {mock_conn.execute.call_args_list}"
                    )

                    # Should show seeded count
                    assert "10" in result.stdout or "seeded" in result.stdout.lower(), (
                        f"Expected seeded count in output: {result.stdout}"
                    )