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
from typing import Optional

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
        env_file='.env',
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

    # Web server settings (WEB-01, WEB-02)
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    cert_path: Path = Path("data/localhost.crt")
    key_path: Path = Path("data/localhost.key")

    # LAN configuration (CERT-01, CERT-02, NET-01)
    lan_enabled: bool = False  # Set via --lan flag in web command
    lan_cert_path: Path = Path("data/lan.crt")  # D-02: Certificate storage
    lan_key_path: Path = Path("data/lan.key")   # D-02: Certificate storage

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


def get_database_path(db_path: Optional[Path] = None) -> Path:
    """Resolve database path with fallback to Settings or default.

    AP-01: Centralized database path resolution to avoid duplicated pattern.

    Priority:
    1. If db_path is provided, use it directly
    2. Try to load from Settings().database_path
    3. Fall back to Path("data/bookmarks.db")

    Args:
        db_path: Optional database path override.

    Returns:
        Resolved Path to the database file.

    Example:
        >>> path = get_database_path()
        >>> path = get_database_path(Path("/custom/path.db"))
    """
    if db_path is not None:
        return db_path
    try:
        return Settings().database_path
    except Exception:
        return Path("data/bookmarks.db")


__all__ = ["Settings", "get_database_path"]