"""X API client wrapper for bookmark operations.

D-05: Dedicated api/x_client.py module wrapping tweepy.Client.

DATA-01: Fetch bookmarked posts from X API.
DATA-04: Handle X API rate limits.
DATA-05: Handle 800 bookmark limit.

Usage:
    from src.api import XClient
    from src.auth import ensure_authenticated

    auth = ensure_authenticated()
    client = XClient(auth.access_token)
    result = client.fetch_bookmarks()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import tweepy


@dataclass
class RateLimitInfo:
    """Rate limit information from X API response headers."""
    remaining: int = 180
    reset_at: float = 0.0  # Unix timestamp

    @property
    def wait_seconds(self) -> float:
        """Seconds until rate limit resets."""
        return max(0, self.reset_at - time.time())


@dataclass
class BookmarkFetchResult:
    """Result from fetching bookmarks.

    Attributes:
        tweets: List of Tweet objects from response.data
        users: Dict mapping user_id to User object (from includes)
        media: Dict mapping media_key to Media object (from includes)
        next_token: Pagination token for next page, or None
        result_count: Number of results in this page
        rate_limit: Rate limit info from response headers
    """
    tweets: list[Any] = field(default_factory=list)
    users: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)
    next_token: Optional[str] = None
    result_count: int = 0
    rate_limit: RateLimitInfo = field(default_factory=RateLimitInfo)


class XClient:
    """Tweepy wrapper for X API bookmark operations.

    D-05: Encapsulates rate limiting logic, pagination state management.
    Returns typed data structures for clean separation of concerns.

    CRITICAL: Must use access_token (OAuth 2.0 User Context), NOT bearer_token.
    Using bearer_token causes 403 Forbidden on bookmarks endpoint.
    """

    # D-03: Expansions for full content (DATA-02)
    EXPANSIONS = "author_id,attachments.media_keys"
    TWEET_FIELDS = "created_at,public_metrics,attachments,entities"
    USER_FIELDS = "username,name,profile_image_url"
    MEDIA_FIELDS = "url,preview_image_url,height,width,alt_text"

    def __init__(self, access_token: str):
        """Initialize client with OAuth 2.0 access token.

        Args:
            access_token: OAuth 2.0 access token from ensure_authenticated().

        Raises:
            ValueError: If access_token is empty.
        """
        if not access_token:
            raise ValueError("access_token required for XClient (OAuth 2.0 User Context)")
        # tweepy uses 'bearer_token' parameter for OAuth 2.0 access tokens
        self._client = tweepy.Client(bearer_token=access_token)
        self._last_response: Optional[Any] = None

    def fetch_bookmarks(
        self,
        max_results: int = 50,  # X API bug: max_results=100 doesn't return next_token
        pagination_token: Optional[str] = None
    ) -> BookmarkFetchResult:
        """Fetch a page of bookmarks from X API.

        DATA-01: Fetch bookmarked posts from X API.
        DATA-04: Returns rate limit info for handling.

        Args:
            max_results: Results per page (max 100).
            pagination_token: Token for next page, or None for first page.

        Returns:
            BookmarkFetchResult with tweets, users, media, pagination info.

        Note:
            Bookmarks are returned newest-first.
            Rate limit: 180 requests / 15 minutes per user.
        """
        response = self._client.get_bookmarks(
            max_results=max_results,
            expansions=self.EXPANSIONS,
            tweet_fields=self.TWEET_FIELDS,
            user_fields=self.USER_FIELDS,
            media_fields=self.MEDIA_FIELDS,
            pagination_token=pagination_token,
        )

        self._last_response = response

        # Extract rate limit info from response headers
        rate_limit = self._extract_rate_limit(response)

        # Build result
        result = BookmarkFetchResult(
            tweets=list(response.data) if response.data else [],
            users={u.id: u for u in response.includes.get('users', [])} if response.includes else {},
            media={m.media_key: m for m in response.includes.get('media', [])} if response.includes else {},
            next_token=response.meta.get('next_token') if response.meta else None,
            result_count=response.meta.get('result_count', 0) if response.meta else 0,
            rate_limit=rate_limit,
        )

        return result

    def _extract_rate_limit(self, response: Any) -> RateLimitInfo:
        """Extract rate limit info from response headers.

        DATA-04: Track x-rate-limit-remaining and x-rate-limit-reset.

        Returns:
            RateLimitInfo with remaining requests and reset timestamp.
        """
        # Tweepy exposes headers via response object
        # Try multiple access patterns for robustness
        headers = getattr(response, 'headers', None)
        if headers is None and hasattr(response, '_response'):
            headers = getattr(response._response, 'headers', {})

        if headers:
            try:
                remaining = int(headers.get('x-rate-limit-remaining', 180))
                reset_at = float(headers.get('x-rate-limit-reset', time.time() + 900))
                return RateLimitInfo(remaining=remaining, reset_at=reset_at)
            except (ValueError, TypeError):
                pass

        # Default if headers unavailable
        return RateLimitInfo(remaining=180, reset_at=time.time() + 900)