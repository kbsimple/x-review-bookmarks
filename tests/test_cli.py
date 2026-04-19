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