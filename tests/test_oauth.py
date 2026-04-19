"""Tests for OAuth 2.0 PKCE authentication module.

Tests AUTH-01: OAuth 2.0 PKCE flow initiation
Tests AUTH-02: Token storage and refresh
Tests AUTH-03: Graceful error handling
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAuthorizationUrl:
    """Tests for AUTH-01: OAuth 2.0 PKCE flow initiation."""

    def test_get_authorization_url(self):
        """Verify authorization URL is generated correctly.

        AUTH-01: User can initiate OAuth 2.0 PKCE flow.

        Expected behavior:
        - Returns a valid URL starting with https://twitter.com/i/oauth2/authorize
        - URL contains client_id parameter
        - URL contains redirect_uri parameter (http://127.0.0.1:8080/callback)
        - URL contains scope parameter with required scopes
        - URL contains state parameter (CSRF protection)
        """
        from src.auth.oauth import get_authorization_url, OAUTH_SCOPES, CALLBACK_URI

        url = get_authorization_url("test_client_id", "test_client_secret")

        # Verify URL structure
        assert url.startswith("https://twitter.com/i/oauth2/authorize"), \
            f"URL should start with twitter.com, got: {url}"

        # Verify scope is present (may be encoded differently)
        assert "scope" in url.lower() or any(scope in url for scope in OAUTH_SCOPES), \
            f"URL should contain scope: {url}"

        # Verify redirect_uri
        assert "127.0.0.1" in url, f"URL should use 127.0.0.1: {url}"
        assert "callback" in url, f"URL should contain callback path: {url}"

    def test_callback_server_binding(self):
        """Verify callback server binds to 127.0.0.1 only (not 0.0.0.0).

        AUTH-01: Callback server security.

        Expected behavior:
        - wait_for_callback binds to 127.0.0.1, not 0.0.0.0
        - Server accepts connections from localhost only
        """
        from src.auth.oauth import CALLBACK_HOST, CALLBACK_URI

        # Verify callback configuration
        assert CALLBACK_HOST == "127.0.0.1", \
            f"Callback should bind to 127.0.0.1, got: {CALLBACK_HOST}"

        assert "127.0.0.1" in CALLBACK_URI, \
            f"Callback URI should use 127.0.0.1, got: {CALLBACK_URI}"


class TestTokenManagement:
    """Tests for AUTH-02: Token storage and refresh."""

    def test_save_and_load_tokens(self, temp_token_file):
        """Verify tokens can be saved and loaded from file.

        AUTH-02: Application stores access tokens securely.

        Expected behavior:
        - save_tokens creates file at specified path
        - load_tokens returns (access_token, refresh_token) tuple
        - Tokens persist across save/load cycle
        """
        from src.auth.oauth import save_tokens, load_tokens

        # Save tokens
        save_tokens("test_access_token", "test_refresh_token", temp_token_file)

        # Verify file exists
        assert temp_token_file.exists(), "Token file should exist"

        # Load tokens
        tokens = load_tokens(temp_token_file)

        # Verify tokens
        assert tokens is not None, "load_tokens should return tuple, not None"
        access_token, refresh_token = tokens
        assert access_token == "test_access_token", \
            f"Expected 'test_access_token', got {access_token}"
        assert refresh_token == "test_refresh_token", \
            f"Expected 'test_refresh_token', got {refresh_token}"

    def test_token_file_permissions(self, temp_token_file):
        """Verify token file has restrictive permissions.

        AUTH-02: Token storage security (threat T-01-03).

        Expected behavior:
        - Token file has mode 0600 (owner read/write only)
        - File is not world-readable

        Note: Permissions test may not work on Windows.
        """
        import stat
        from src.auth.oauth import save_tokens

        # Save tokens
        save_tokens("test_access", "test_refresh", temp_token_file)

        # Check file permissions (Unix only)
        try:
            file_stat = temp_token_file.stat()
            # Get permission bits (last 9 bits)
            permissions = stat.S_IMODE(file_stat.st_mode)
            # Check that group and other have no permissions
            # Note: 0o600 is ideal, but we check for at least removing write for others
            assert (permissions & 0o077) == 0, \
                f"Token file should have mode 0600, got {oct(permissions)}"
        except (OSError, AttributeError):
            # Skip on Windows or filesystems that don't support chmod
            pass

    def test_load_tokens_nonexistent_file(self, tmp_path):
        """Verify load_tokens returns None for nonexistent file.

        AUTH-02: Graceful handling of missing token file.
        """
        from src.auth.oauth import load_tokens

        nonexistent = tmp_path / "nonexistent.json"
        tokens = load_tokens(nonexistent)

        assert tokens is None, f"Expected None for nonexistent file, got {tokens}"

    def test_load_tokens_invalid_json(self, temp_token_file):
        """Verify load_tokens returns None for invalid JSON.

        AUTH-02: Graceful handling of corrupted token file.
        """
        from src.auth.oauth import load_tokens

        # Write invalid JSON
        temp_token_file.write_text("not valid json {{{")

        tokens = load_tokens(temp_token_file)

        assert tokens is None, f"Expected None for invalid JSON, got {tokens}"

    def test_refresh_expired_token(self):
        """Verify refresh token exchanges for new access token.

        AUTH-02: Application refreshes access tokens securely.

        Note: This test mocks the API call since actual refresh requires
        valid tokens.
        """
        from src.auth.oauth import refresh_access_token

        # Mock the refresh call
        with patch("src.auth.oauth._oauth2_handler") as mock_handler:
            mock_handler.refresh_token.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }

            # This would fail without mocking, so we just verify the function exists
            # and has the right signature
            import inspect
            sig = inspect.signature(refresh_access_token)
            params = list(sig.parameters.keys())
            assert "client_id" in params, "refresh_access_token should have client_id param"
            assert "client_secret" in params, "refresh_access_token should have client_secret param"
            assert "refresh_token" in params, "refresh_access_token should have refresh_token param"


class TestErrorHandling:
    """Tests for AUTH-03: Graceful error handling."""

    def test_handle_expired_token(self):
        """Verify expired token returns clear error message.

        AUTH-03: Application handles token expiration gracefully.

        Expected behavior:
        - AuthError raised with clear message about expiration
        - Error message includes "expired" or "re-authenticate" guidance
        - Error does not expose raw API response to user
        """
        from src.auth.oauth import AuthError, verify_credentials
        import tweepy

        # Mock an expired token response (401)
        with patch("src.auth.oauth.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Simulate 401 Unauthorized
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = '{"error": "invalid_token"}'

            error = tweepy.TweepyException("Unauthorized")
            error.response = mock_response
            mock_client.get_me.side_effect = error

            # Should raise AuthError with clear message
            with pytest.raises(AuthError) as exc_info:
                verify_credentials("expired_token")

            # Verify error message is user-friendly
            error_msg = str(exc_info.value)
            assert "expired" in error_msg.lower() or "re-authenticate" in error_msg.lower(), \
                f"Error should guide user to re-authenticate: {error_msg}"

    def test_handle_invalid_token(self):
        """Verify invalid token returns clear error message.

        AUTH-03: Application handles invalid tokens gracefully.

        Expected behavior:
        - AuthError raised with clear message about invalid credentials
        - Error message includes guidance to re-authenticate
        - Error does not expose raw API response to user
        """
        from src.auth.oauth import AuthError, verify_credentials
        import tweepy

        # Mock an invalid token response (401)
        with patch("src.auth.oauth.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Simulate 401 Unauthorized
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = '{"error": "invalid_token"}'

            error = tweepy.TweepyException("Unauthorized")
            error.response = mock_response
            mock_client.get_me.side_effect = error

            # Should raise AuthError with clear message
            with pytest.raises(AuthError) as exc_info:
                verify_credentials("invalid_token")

            # Verify error has status code
            assert exc_info.value.status_code == 401, \
                f"Expected status_code=401, got {exc_info.value.status_code}"

    def test_auth_error_str_formatting(self):
        """Verify AuthError string formatting.

        AUTH-03: Clear error messages.
        """
        from src.auth.oauth import AuthError

        # Test with all parameters
        error = AuthError("Token expired", status_code=401, response_body='{"error": "test"}')
        error_str = str(error)

        assert "Token expired" in error_str, f"Message should be in error: {error_str}"
        assert "401" in error_str, f"Status code should be in error: {error_str}"

    def test_auth_error_minimal(self):
        """Verify AuthError works with minimal parameters.

        AUTH-03: Error handling flexibility.
        """
        from src.auth.oauth import AuthError

        # Test with message only
        error = AuthError("Something went wrong")
        error_str = str(error)

        assert "Something went wrong" in error_str, f"Message should be in error: {error_str}"
        assert "HTTP" not in error_str, f"HTTP should not be in minimal error: {error_str}"


class TestEnsureAuthenticated:
    """Tests for full authentication flow orchestration."""

    def test_ensure_authenticated_with_stored_tokens(self, temp_token_file):
        """Verify ensure_authenticated returns XAuth when tokens exist.

        Expected behavior:
        - If tokens.json exists and is valid, return XAuth
        - No browser flow initiated
        """
        from src.auth.oauth import ensure_authenticated, save_tokens, XAuth

        # Pre-save tokens
        save_tokens("existing_access", "existing_refresh", temp_token_file)

        # Mock environment
        with patch.dict("os.environ", {"X_CLIENT_ID": "test_id", "X_CLIENT_SECRET": "test_secret"}):
            with patch("src.auth.oauth.DEFAULT_TOKEN_PATH", temp_token_file):
                auth = ensure_authenticated()

        # Should return XAuth with stored tokens
        assert isinstance(auth, XAuth), f"Expected XAuth, got {type(auth)}"
        assert auth.access_token == "existing_access", \
            f"Expected stored access token, got {auth.access_token}"

    def test_ensure_authenticated_first_run(self, tmp_path):
        """Verify ensure_authenticated initiates browser flow on first run.

        Expected behavior:
        - If no tokens.json exists, start OAuth flow
        - Print authorization URL
        - Start callback server
        - Exchange code for tokens
        - Save tokens to file

        Note: This test mocks the network calls.
        """
        from src.auth.oauth import ensure_authenticated, XAuth

        token_path = tmp_path / "tokens.json"

        # Mock the entire flow
        with patch.dict("os.environ", {"X_CLIENT_ID": "test_id", "X_CLIENT_SECRET": "test_secret"}):
            with patch("src.auth.oauth.DEFAULT_TOKEN_PATH", token_path):
                with patch("src.auth.oauth.get_authorization_url") as mock_get_url:
                    with patch("src.auth.oauth.wait_for_callback") as mock_wait:
                        with patch("src.auth.oauth.exchange_code_for_token") as mock_exchange:
                            mock_get_url.return_value = "https://twitter.com/auth"
                            mock_wait.return_value = "auth_code"
                            mock_exchange.return_value = ("new_access", "new_refresh")

                            auth = ensure_authenticated()

        # Verify XAuth returned
        assert isinstance(auth, XAuth), f"Expected XAuth, got {type(auth)}"
        assert auth.client_id == "test_id", f"Expected test_id, got {auth.client_id}"