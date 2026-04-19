"""OAuth 2.0 PKCE authentication with X API.

Provides:
- XAuth: Credentials dataclass for OAuth 2.0 tokens
- AuthError: Exception for authentication failures
- ensure_authenticated: Orchestrate full OAuth flow
- get_authorization_url: Generate PKCE authorization URL
- wait_for_callback: Start local server for OAuth callback
- exchange_code_for_token: Exchange authorization code for tokens
- save_tokens: Persist tokens to file
- load_tokens: Load tokens from file

Usage:
    from src.auth import ensure_authenticated

    # First run: opens browser for authorization
    auth = ensure_authenticated()

    # Subsequent runs: uses stored tokens
    auth = ensure_authenticated()
"""

from .oauth import (
    XAuth,
    AuthError,
    ensure_authenticated,
    get_authorization_url,
    wait_for_callback,
    exchange_code_for_token,
    save_tokens,
    load_tokens,
)

__all__ = [
    "XAuth",
    "AuthError",
    "ensure_authenticated",
    "get_authorization_url",
    "wait_for_callback",
    "exchange_code_for_token",
    "save_tokens",
    "load_tokens",
]