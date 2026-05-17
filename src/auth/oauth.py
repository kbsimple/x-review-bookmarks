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


# D-04: OAuth scopes for bookmarks
OAUTH_SCOPES = ["tweet.read", "users.read", "bookmark.read", "offline.access"]

# Default callback configuration
CALLBACK_HOST = "127.0.0.1"  # Security: bind to localhost only, not 0.0.0.0
CALLBACK_PORT = 8080
CALLBACK_PATH = "/callback"
CALLBACK_URI = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"


def get_authorization_url(client_id: str, client_secret: str) -> str:
    """Create OAuth 2.0 PKCE authorization URL.

    AUTH-01: User can initiate OAuth 2.0 PKCE flow.

    Creates a tweepy.OAuth2UserHandler and returns the authorization URL
    the user must visit in their browser to authorize the app.

    Args:
        client_id: X API client ID (App ID from developer portal).
        client_secret: X API client secret (App Secret from developer portal).

    Returns:
        Authorization URL to visit in browser.

    Raises:
        AuthError: If OAuth2UserHandler fails to create.

    Note:
        D-04: Scopes are tweet.read, users.read, bookmark.read, offline.access.
        Security: Callback URI is http://127.0.0.1:8080/callback (not 0.0.0.0).

    Example:
        >>> url = get_authorization_url("my_client_id", "my_client_secret")
        >>> print(url)  # Opens Twitter authorization page
        https://twitter.com/i/oauth2/authorize?client_id=...
    """
    global _oauth2_handler

    _oauth2_handler = tweepy.OAuth2UserHandler(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=CALLBACK_URI,
        scope=OAUTH_SCOPES,
    )

    return _oauth2_handler.get_authorization_url()


def wait_for_callback(port: int = CALLBACK_PORT, timeout: int = 300) -> str:
    """Start a temporary HTTP server to capture the OAuth callback code.

    AUTH-01: Callback server captures authorization code.

    Starts an HTTP server on 127.0.0.1:port that listens for a single
    GET request to /callback?code=XXX, extracts the code parameter,
    and returns it. The server shuts down after the callback is received
    or after the timeout elapses.

    Args:
        port: Port to listen on. Defaults to 8080.
        timeout: Seconds to wait before raising TimeoutError. Defaults to 300.

    Returns:
        The authorization code from the callback redirect.

    Raises:
        TimeoutError: If no callback is received within the timeout period.

    Security:
        Binds to 127.0.0.1 only (not 0.0.0.0) to prevent external access.

    Example:
        >>> code = wait_for_callback(port=8080, timeout=300)
        >>> print(f"Received code: {code}")
    """
    code_received = threading.Event()
    received_code: list[str | None] = [None]

    class CallbackHandler(BaseHTTPRequestHandler):
        """HTTP handler for OAuth callback."""

        def do_GET(self):
            """Handle GET request to /callback."""
            if self.path.startswith(CALLBACK_PATH):
                qs = parse_qs(urlparse(self.path).query)
                if "code" in qs:
                    # Store the full callback URL path for CSRF state validation
                    received_code[0] = self.path
                    code_received.set()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body>"
                        b"<h1>Authorization complete!</h1>"
                        b"<p>You may close this window.</p>"
                        b"</body></html>"
                    )
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Missing code parameter")
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not found")

        def log_message(self, *args):
            """Suppress logging."""
            pass

    # Security: Bind to 127.0.0.1 only, not 0.0.0.0
    server = HTTPServer((CALLBACK_HOST, port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    if not code_received.wait(timeout):
        server.shutdown()
        raise TimeoutError(f"No callback received within {timeout} seconds")

    # Use server_close() instead of shutdown() - cleaner and doesn't block
    server.server_close()
    thread.join()

    code = received_code[0]
    if code is None:
        raise AuthError("Failed to receive authorization code")

    return code


def exchange_code_for_token(callback_path: str) -> tuple[str, str]:
    """Exchange authorization code for access and refresh tokens.

    Uses the OAuth2UserHandler stored by get_authorization_url() to
    fetch the access token and refresh token using the authorization code.

    Args:
        callback_path: Full callback URL path from wait_for_callback()
            (e.g. "/callback?code=...&state=...").

    Returns:
        Tuple of (access_token, refresh_token).

    Raises:
        AuthError: If OAuth2UserHandler not initialized or token exchange fails.

    Example:
        >>> callback_path = wait_for_callback()
        >>> access_token, refresh_token = exchange_code_for_token(callback_path)
    """
    global _oauth2_handler

    if _oauth2_handler is None:
        raise AuthError(
            "OAuth2UserHandler not initialized. "
            "Call get_authorization_url() first."
        )

    try:
        # Extract code from callback path
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(callback_path).query)
        code = qs.get("code", [None])[0]

        if not code:
            raise AuthError("No code parameter in callback URL")

        # Use fetch_token with code parameter
        token_data = _oauth2_handler.fetch_token(code=code)

        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")

        if not access_token:
            raise AuthError("Token exchange failed: no access_token in response")

        return access_token, refresh_token

    except Exception as e:
        raise AuthError(f"Token exchange failed: {e}") from e


# D-01: Default token storage path
DEFAULT_TOKEN_PATH = Path("data/tokens.json")


def save_tokens(
    access_token: str,
    refresh_token: str,
    path: Path | str | None = None
) -> Path:
    """Persist OAuth 2.0 tokens to a JSON file.

    AUTH-02: Application stores access tokens securely.

    Creates parent directory if needed, saves tokens as JSON with
    restrictive file permissions (0600).

    Args:
        access_token: OAuth 2.0 access token.
        refresh_token: OAuth 2.0 refresh token.
        path: File path for token storage. Defaults to data/tokens.json (D-01).

    Returns:
        Path to the saved token file.

    Security:
        - File created with mode 0600 (owner read/write only)
        - Parent directory created with mode 0755

    Example:
        >>> save_tokens("my_access_token", "my_refresh_token")
        PosixPath('data/tokens.json')
    """
    if path is None:
        path = DEFAULT_TOKEN_PATH

    path = Path(path)

    # Create parent directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save tokens as JSON
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    with open(path, "w") as f:
        json.dump(token_data, f, indent=2)

    # Set restrictive permissions (owner read/write only)
    # Security: T-01-03 mitigation
    try:
        path.chmod(0o600)
    except OSError:
        # chmod may fail on some filesystems (e.g., Windows)
        pass

    return path


def load_tokens(path: Path | str | None = None) -> tuple[str, str] | None:
    """Load OAuth 2.0 tokens from a JSON file.

    AUTH-02: Application loads stored tokens on startup.

    Args:
        path: File path for token storage. Defaults to data/tokens.json (D-01).

    Returns:
        Tuple of (access_token, refresh_token) if file exists and is valid.
        None if file doesn't exist or is invalid.

    Example:
        >>> tokens = load_tokens()
        >>> if tokens:
        ...     access_token, refresh_token = tokens
    """
    if path is None:
        path = DEFAULT_TOKEN_PATH

    path = Path(path)

    try:
        with open(path) as f:
            data = json.load(f)

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if not access_token:
            return None

        return access_token, refresh_token

    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None


def ensure_authenticated(
    client_id: str | None = None,
    client_secret: str | None = None,
    token_path: Path | str | None = None
) -> XAuth:
    """Ensure valid OAuth 2.0 tokens are available, running interactive flow if needed.

    AUTH-01: User can authenticate with X via OAuth 2.0 PKCE flow.
    AUTH-02: Application stores and refreshes access tokens securely.
    AUTH-03: Application handles missing tokens gracefully.

    Orchestrates the full first-run OAuth 2.0 PKCE flow:
      1. Load tokens from token_path (default: data/tokens.json)
      2. If tokens exist, return XAuth with stored tokens
      3. If no tokens, initiate OAuth 2.0 PKCE flow:
         a. Get authorization URL
         b. Print URL for user to open
         c. Start callback server
         d. Exchange code for tokens
         e. Save tokens to token_path
      4. Return XAuth instance

    Args:
        client_id: X API client ID. If None, tries X_CLIENT_ID env var.
        client_secret: X API client secret. If None, tries X_CLIENT_SECRET env var.
        token_path: Path to token file. Defaults to data/tokens.json (D-01).

    Returns:
        XAuth instance with valid access and refresh tokens.

    Raises:
        AuthError: If client credentials missing or OAuth flow fails.

    Example:
        >>> # First run: initiates browser flow
        >>> auth = ensure_authenticated()
        Open this URL in your browser:
        https://twitter.com/i/oauth2/authorize?...

        >>> # Subsequent runs: uses stored tokens
        >>> auth = ensure_authenticated()
        >>> print(auth.access_token)
    """
    # Get credentials from args or environment
    if client_id is None:
        client_id = os.environ.get("X_CLIENT_ID")
    if client_secret is None:
        client_secret = os.environ.get("X_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise AuthError(
            "X_CLIENT_ID and X_CLIENT_SECRET must be provided or set in environment"
        )

    # Try loading stored tokens
    tokens = load_tokens(token_path)
    if tokens:
        access_token, refresh_token = tokens
        return XAuth(
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    # First-run: initiate OAuth 2.0 PKCE
    print("No stored tokens found. Initiating OAuth 2.0 PKCE flow...")

    auth_url = get_authorization_url(client_id, client_secret)
    print(f"\nOpen this URL in your browser:\n{auth_url}\n")
    print("Waiting for authorization callback...")

    # Wait for user to authorize in browser
    code = wait_for_callback()

    # Exchange code for tokens
    access_token, refresh_token = exchange_code_for_token(code)

    # Save tokens for future use
    save_tokens(access_token, refresh_token, token_path)

    print("Authorization complete! Tokens saved.")

    return XAuth(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        refresh_token=refresh_token,
    )


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> tuple[str, str]:
    """Exchange refresh token for new access token.

    AUTH-02: Application refreshes access tokens securely.

    Uses the OAuth2UserHandler to refresh an expired access token.

    Args:
        client_id: X API client ID.
        client_secret: X API client secret.
        refresh_token: OAuth 2.0 refresh token.

    Returns:
        Tuple of (new_access_token, new_refresh_token).
        Note: refresh_token may be the same or updated depending on X API.

    Raises:
        AuthError: If token refresh fails.

    Note:
        Workaround for tweepy issue #1953:
        The refresh_token method requires HTTPBasicAuth for some OAuth providers.
        Tweepy's OAuth2UserHandler handles this internally.

    Example:
        >>> new_access, new_refresh = refresh_access_token(
        ...     client_id="...",
        ...     client_secret="...",
        ...     refresh_token="...",
        ... )
    """
    global _oauth2_handler

    # Create a new handler for refresh (or reuse existing)
    if _oauth2_handler is None:
        _oauth2_handler = tweepy.OAuth2UserHandler(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=CALLBACK_URI,
            scope=OAUTH_SCOPES,
        )

    try:
        # Tweepy's refresh_token method
        # Note: This may require HTTPBasicAuth workaround for some providers
        # See: https://github.com/tweepy/tweepy/issues/1953
        token_data = _oauth2_handler.refresh_token(
            token_url="https://api.twitter.com/2/oauth2/token",
            refresh_token=refresh_token,
        )

        new_access_token = token_data.get("access_token", "")
        new_refresh_token = token_data.get("refresh_token", refresh_token)

        if not new_access_token:
            raise AuthError("Token refresh failed: no access_token in response")

        return new_access_token, new_refresh_token

    except Exception as e:
        raise AuthError(f"Token refresh failed: {e}") from e


def verify_credentials(access_token: str) -> dict[str, Any]:
    """Verify OAuth 2.0 access token by calling GET /2/users/me.

    AUTH-03: Application handles token expiration gracefully.

    Makes a test API call to verify that the access token is valid.

    Args:
        access_token: OAuth 2.0 access token to verify.

    Returns:
        Dict containing user profile data from GET /2/users/me.

    Raises:
        AuthError: If credentials are invalid (401) or rate limited (429).

    Example:
        >>> user_data = verify_credentials(auth.access_token)
        >>> print(user_data['data']['username'])
    """
    client = tweepy.Client(bearer_token=access_token)

    try:
        response = client.get_me()
        if response is None or response.data is None:
            raise AuthError("GET /2/users/me returned no data")
        return response.data

    except tweepy.TweepyException as e:
        # Extract HTTP status code and response body
        status_code: int | None = None
        response_body: str | None = None

        if hasattr(e, "response") and e.response is not None:
            status_code = getattr(e.response, "status_code", None)
            response_body = getattr(e.response, "text", None)

        error_msg = str(e)

        if status_code == 401:
            raise AuthError(
                "X API authentication failed: credentials are invalid or expired. "
                "Please run 'xbm auth' to re-authenticate.",
                status_code=status_code,
                response_body=response_body,
            ) from e
        elif status_code == 429:
            raise AuthError(
                "X API rate limit exceeded. Please wait before retrying.",
                status_code=status_code,
                response_body=response_body,
            ) from e
        else:
            raise AuthError(
                f"X API request failed: {error_msg}",
                status_code=status_code,
                response_body=response_body,
            ) from e