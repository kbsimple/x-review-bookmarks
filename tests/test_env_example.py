"""Tests for .env.example template file."""

import pytest
from pathlib import Path


class TestEnvExample:
    """Tests for .env.example file."""

    def test_env_example_exists(self):
        """Test 1: .env.example file exists."""
        env_example = Path(".env.example")
        assert env_example.exists(), ".env.example file should exist"

    def test_env_example_contains_client_id(self):
        """Test 2: File contains X_CLIENT_ID= placeholder."""
        content = Path(".env.example").read_text()
        assert "X_CLIENT_ID=" in content, "Should contain X_CLIENT_ID placeholder"

    def test_env_example_contains_client_secret(self):
        """Test 3: File contains X_CLIENT_SECRET= placeholder."""
        content = Path(".env.example").read_text()
        assert "X_CLIENT_SECRET=" in content, "Should contain X_CLIENT_SECRET placeholder"

    def test_env_example_contains_token_path(self):
        """File documents X_TOKEN_PATH with default."""
        content = Path(".env.example").read_text()
        assert "X_TOKEN_PATH=" in content, "Should document X_TOKEN_PATH"

    def test_env_example_contains_database_path(self):
        """File documents X_DATABASE_PATH with default."""
        content = Path(".env.example").read_text()
        assert "X_DATABASE_PATH=" in content, "Should document X_DATABASE_PATH"

    def test_env_example_has_instructions(self):
        """File includes instructions for obtaining credentials."""
        content = Path(".env.example").read_text()
        assert "developer.twitter.com" in content or "X API" in content.lower(), "Should mention where to get credentials"