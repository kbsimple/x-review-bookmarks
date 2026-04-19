"""OAuth 2.0 PKCE authentication with X API.

Implements:
- AUTH-01: OAuth 2.0 PKCE flow initiation
- AUTH-02: Token storage and refresh
- AUTH-03: Graceful error handling

Adapted from x-api/src/auth/x_auth.py reference implementation.

Usage:
    from src.auth import ensure_authenticated, XAuth

    # First run: initiates browser flow
    auth = ensure_authenticated()

    # Subsequent runs: uses stored tokens
    auth = ensure_authenticated()
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import tweepy


class AuthError(Exception):
    """Raised when X API authentication fails or credentials are missing.

    AUTH-03: Provides clear error messages for authentication failures.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if available (e.g. 401, 429).
        response_body: Raw response body for debugging.

    Example:
        >>> raise AuthError("Token expired", status_code=401)
        AuthError: Token expired (HTTP 401)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        """Format error message with optional status code and response body."""
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"(HTTP {self.status_code})")
        if self.response_body:
            # Truncate response body for readability
            body_preview = self.response_body[:200]
            parts.append(f"Response: {body_preview}")
        return " ".join(parts)


@dataclass
class XAuth:
    """X API OAuth 2.0 PKCE credentials.

    Stores all credentials needed for X API authentication:
    - client_id, client_secret: OAuth app credentials
    - access_token, refresh_token: User-specific tokens

    Attributes:
        client_id: X API client ID (App ID from developer portal).
        client_secret: X API client secret (App Secret from developer portal).
        access_token: OAuth 2.0 access token (Bearer token, expires ~2 hours).
        refresh_token: OAuth 2.0 refresh token (long-lived, for token refresh).

    Example:
        >>> auth = XAuth(
        ...     client_id="your_client_id",
        ...     client_secret="your_client_secret",
        ...     access_token="your_access_token",
        ...     refresh_token="your_refresh_token",
        ... )
    """

    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str


# Module-level OAuth2UserHandler instance for PKCE flow
# Stored after get_authorization_url() call, used by exchange_code_for_token()
_oauth2_handler: tweepy.OAuth2UserHandler | None = None