"""Configuration settings using Pydantic Settings.

Provides type-safe configuration from environment variables with:
- X_CLIENT_ID: Required X API client ID
- X_CLIENT_SECRET: Required X API client secret (SecretStr for safety)
- X_ACCESS_TOKEN: Optional OAuth access token
- X_REFRESH_TOKEN: Optional OAuth refresh token
- X_TOKEN_PATH: Optional path to token file (default: data/tokens.json)
- X_DATABASE_PATH: Optional path to database (default: data/bookmarks.db)

Usage:
    from src.config import Settings

    settings = Settings()  # Raises ValidationError if X_CLIENT_ID missing
    client_id = settings.client_id
    secret = settings.client_secret_value  # Access actual secret value
"""

from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    D-01: Token storage defaults to data/tokens.json, configurable via settings.
    D-02: SQLite database stored at data/bookmarks.db.
    D-04: OAuth scopes (client credentials): tweet.read, users.read, bookmark.read, offline.access.

    Environment variables (all prefixed with X_):
        X_CLIENT_ID: X API client ID (required)
        X_CLIENT_SECRET: X API client secret (required, stored as SecretStr)
        X_ACCESS_TOKEN: OAuth 2.0 access token (optional, loaded from tokens.json)
        X_REFRESH_TOKEN: OAuth 2.0 refresh token (optional, loaded from tokens.json)
        X_TOKEN_PATH: Path to token file (default: data/tokens.json)
        X_DATABASE_PATH: Path to database file (default: data/bookmarks.db)

    Example:
        >>> settings = Settings()
        >>> settings.client_id
        'your-client-id'
        >>> settings.client_secret
        SecretStr('**********')
        >>> settings.client_secret_value
        'your-client-secret'
    """

    model_config = SettingsConfigDict(
        env_prefix='X_',              # X_CLIENT_ID, X_CLIENT_SECRET, etc.
        env_file='.env.local',
        case_sensitive=False,
        extra='ignore',               # Ignore extra env vars
    )

    # Required credentials - fail at startup if missing
    client_id: str
    client_secret: SecretStr         # Hidden from logs/repr (D-01 security)

    # Optional with defaults (loaded from tokens.json after first auth)
    access_token: str = ""
    refresh_token: str = ""

    # Configurable paths (D-01, D-02)
    token_path: Path = Path("data/tokens.json")
    database_path: Path = Path("data/bookmarks.db")

    @property
    def client_secret_value(self) -> str:
        """Access the actual secret value.

        Returns:
            The plain text client secret.

        Note:
            Use this property sparingly. The SecretStr type prevents
            accidental logging of secrets via repr() or str().
        """
        return self.client_secret.get_secret_value()


__all__ = ["Settings"]