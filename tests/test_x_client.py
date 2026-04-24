"""Tests for X API client wrapper.

Tests for:
- get_bookmarks pagination
- Rate limit handling
- Media/author expansion
- Authentication with OAuth 2.0 User Context
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestXClient:
    """Tests for XClient wrapper around tweepy.Client."""

    def test_x_client_init_requires_access_token(self):
        """Verify XClient raises ValueError on empty access_token.

        CRITICAL: XClient must use access_token (OAuth 2.0 User Context),
        not bearer_token which causes 403 Forbidden on bookmarks endpoint.
        """
        # Import here to allow test to run before module exists
        from src.api.x_client import XClient

        with pytest.raises(ValueError, match="access_token required"):
            XClient("")

    def test_x_client_uses_access_token_not_bearer(self):
        """Verify XClient passes access_token to tweepy.Client.

        D-05: Dedicated api/x_client.py module wrapping tweepy.Client.
        Must use access_token parameter, NOT bearer_token.
        """
        from src.api.x_client import XClient

        with patch("src.api.x_client.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            client = XClient("test_access_token_123")

            # Verify tweepy.Client was called with access_token, not bearer_token
            mock_client_class.assert_called_once_with(access_token="test_access_token_123")

    def test_fetch_bookmarks_returns_result(self):
        """Verify fetch_bookmarks returns BookmarkFetchResult with correct structure.

        DATA-01: Fetch bookmarked posts from X API.
        """
        from src.api.x_client import XClient, BookmarkFetchResult

        with patch("src.api.x_client.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Mock response with data
            mock_tweet = MagicMock()
            mock_tweet.id = "tweet_123"

            mock_user = MagicMock()
            mock_user.id = "user_456"

            mock_media = MagicMock()
            mock_media.media_key = "media_789"

            mock_response = MagicMock()
            mock_response.data = [mock_tweet]
            mock_response.includes = {
                "users": [mock_user],
                "media": [mock_media],
            }
            mock_response.meta = {"next_token": "next_abc", "result_count": 1}
            mock_response.headers = {}

            mock_client.get_bookmarks.return_value = mock_response

            client = XClient("test_token")
            result = client.fetch_bookmarks()

            assert isinstance(result, BookmarkFetchResult)
            assert len(result.tweets) == 1
            assert result.next_token == "next_abc"
            assert result.result_count == 1

    def test_fetch_bookmarks_extracts_rate_limit(self):
        """Verify fetch_bookmarks extracts rate limit info from headers.

        DATA-04: Handle X API rate limits.
        """
        from src.api.x_client import XClient, RateLimitInfo

        with patch("src.api.x_client.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = []
            mock_response.includes = None
            mock_response.meta = {}
            # Simulate headers from X API
            mock_response.headers = {
                "x-rate-limit-remaining": "150",
                "x-rate-limit-reset": "1700000000",
            }

            mock_client.get_bookmarks.return_value = mock_response

            client = XClient("test_token")
            result = client.fetch_bookmarks()

            assert result.rate_limit.remaining == 150
            assert result.rate_limit.reset_at == 1700000000.0

    def test_fetch_bookmarks_handles_empty_response(self):
        """Verify fetch_bookmarks handles None data gracefully.

        X API may return empty data if no bookmarks exist.
        """
        from src.api.x_client import XClient, BookmarkFetchResult

        with patch("src.api.x_client.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = None
            mock_response.includes = None
            mock_response.meta = None
            mock_response.headers = {}

            mock_client.get_bookmarks.return_value = mock_response

            client = XClient("test_token")
            result = client.fetch_bookmarks()

            assert isinstance(result, BookmarkFetchResult)
            assert result.tweets == []
            assert result.users == {}
            assert result.media == {}
            assert result.next_token is None
            assert result.result_count == 0

    def test_fetch_bookmarks_with_pagination_token(self):
        """Verify fetch_bookmarks passes pagination_token to API.

        DATA-04: Sync handles rate limits gracefully and can resume.
        """
        from src.api.x_client import XClient

        with patch("src.api.x_client.tweepy.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = []
            mock_response.includes = None
            mock_response.meta = {}
            mock_response.headers = {}

            mock_client.get_bookmarks.return_value = mock_response

            client = XClient("test_token")
            client.fetch_bookmarks(pagination_token="resume_token_xyz")

            # Verify pagination_token was passed
            call_kwargs = mock_client.get_bookmarks.call_args[1]
            assert call_kwargs["pagination_token"] == "resume_token_xyz"


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass."""

    def test_wait_seconds_calculation(self):
        """Verify wait_seconds returns correct time until reset."""
        import time
        from src.api.x_client import RateLimitInfo

        # Set reset_at to 100 seconds in the future
        future_time = time.time() + 100
        rate_limit = RateLimitInfo(remaining=10, reset_at=future_time)

        # Should be approximately 100 seconds
        assert 99 <= rate_limit.wait_seconds <= 100

    def test_wait_seconds_negative_when_expired(self):
        """Verify wait_seconds returns 0 when reset time has passed."""
        import time
        from src.api.x_client import RateLimitInfo

        # Set reset_at to 100 seconds in the past
        past_time = time.time() - 100
        rate_limit = RateLimitInfo(remaining=0, reset_at=past_time)

        assert rate_limit.wait_seconds == 0


class TestBookmarkFetchResult:
    """Tests for BookmarkFetchResult dataclass."""

    def test_default_values(self):
        """Verify BookmarkFetchResult has sensible defaults."""
        from src.api.x_client import BookmarkFetchResult

        result = BookmarkFetchResult()

        assert result.tweets == []
        assert result.users == {}
        assert result.media == {}
        assert result.next_token is None
        assert result.result_count == 0