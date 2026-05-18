"""Tests for Settings class in src/config/settings.py."""

import pytest
from pathlib import Path
from pydantic import ValidationError
from pydantic import SecretStr

from src.config import Settings


class TestSettingsRequiredFields:
    """Tests for required field validation."""

    def test_settings_raises_error_when_client_id_missing(self, monkeypatch):
        """Test 1: Settings() raises ValidationError when X_CLIENT_ID missing."""
        # Clear env vars so Settings() can't load from environment
        monkeypatch.delenv("X_CLIENT_ID", raising=False)
        monkeypatch.delenv("X_CLIENT_SECRET", raising=False)

        # Override .env file location to prevent loading from file
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=Path("/dev/null"))
        assert "client_id" in str(exc_info.value).lower()

    def test_settings_raises_error_when_client_secret_missing(self, monkeypatch):
        """Settings() raises ValidationError when X_CLIENT_SECRET missing."""
        # Clear env vars so Settings() can't load from environment
        monkeypatch.delenv("X_CLIENT_ID", raising=False)
        monkeypatch.delenv("X_CLIENT_SECRET", raising=False)

        # Override .env file location to prevent loading from file
        with pytest.raises(ValidationError) as exc_info:
            Settings(client_id="test", _env_file=Path("/dev/null"))
        assert "client_secret" in str(exc_info.value).lower()


class TestSettingsCreation:
    """Tests for Settings instance creation."""

    def test_settings_creates_with_required_fields(self):
        """Test 2: Settings(client_id='test', client_secret='secret') creates instance."""
        settings = Settings(client_id="test", client_secret="secret")
        assert settings.client_id == "test"

    def test_settings_client_secret_is_secret_str(self):
        """Test 3: settings.client_secret returns SecretStr, not plain string."""
        settings = Settings(client_id="test", client_secret="secret")
        assert isinstance(settings.client_secret, SecretStr)

    def test_settings_client_secret_value_returns_string(self):
        """Test 4: settings.client_secret_value returns actual string."""
        settings = Settings(client_id="test", client_secret="my_secret_value")
        assert settings.client_secret_value == "my_secret_value"


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_settings_token_path_defaults_to_data_tokens_json(self):
        """Test 5: settings.token_path defaults to Path('data/tokens.json')."""
        settings = Settings(client_id="test", client_secret="secret")
        assert settings.token_path == Path("data/tokens.json")

    def test_settings_database_path_defaults_to_data_bookmarks_db(self):
        """Test 6: settings.database_path defaults to Path('data/bookmarks.db')."""
        settings = Settings(client_id="test", client_secret="secret")
        assert settings.database_path == Path("data/bookmarks.db")


class TestSettingsEnvironmentVariables:
    """Tests for loading from environment variables."""

    def test_settings_loads_client_id_from_env(self, monkeypatch):
        """Settings loads X_CLIENT_ID from environment."""
        monkeypatch.setenv("X_CLIENT_ID", "env_client_id")
        monkeypatch.setenv("X_CLIENT_SECRET", "env_secret")
        settings = Settings()
        assert settings.client_id == "env_client_id"

    def test_settings_loads_client_secret_from_env(self, monkeypatch):
        """Settings loads X_CLIENT_SECRET from environment."""
        monkeypatch.setenv("X_CLIENT_ID", "env_client_id")
        monkeypatch.setenv("X_CLIENT_SECRET", "env_secret_value")
        settings = Settings()
        assert settings.client_secret_value == "env_secret_value"

    def test_settings_uses_env_prefix(self, monkeypatch):
        """Settings uses X_ prefix for environment variables."""
        monkeypatch.setenv("X_CLIENT_ID", "prefixed_id")
        monkeypatch.setenv("X_CLIENT_SECRET", "prefixed_secret")
        # Non-prefixed should not be used
        monkeypatch.delenv("CLIENT_ID", raising=False)
        monkeypatch.delenv("CLIENT_SECRET", raising=False)
        settings = Settings()
        assert settings.client_id == "prefixed_id"


class TestSettingsOptionalFields:
    """Tests for optional Settings fields."""

    def test_settings_access_token_defaults_to_empty_string(self):
        """access_token defaults to empty string."""
        settings = Settings(client_id="test", client_secret="secret")
        assert settings.access_token == ""

    def test_settings_refresh_token_defaults_to_empty_string(self):
        """refresh_token defaults to empty string."""
        settings = Settings(client_id="test", client_secret="secret")
        assert settings.refresh_token == ""