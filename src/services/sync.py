"""Sync service for bookmark fetching and storage.

D-02: Incremental sync via bookmark ID comparison.
D-03: Auto-wait rate limit handling with pagination token persistence.
DATA-04: Handle X API rate limits (180 requests/15min).
DATA-05: Handle 800 bookmark API limit.
STOR-03: Incremental sync (only fetch new bookmarks).

Usage:
    from src.services import SyncService
    from src.auth import ensure_authenticated
    from src.db import get_connection

    auth = ensure_authenticated()
    conn = get_connection()
    sync_service = SyncService(auth.access_token, conn)
    result = sync_service.sync()
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..api.x_client import BookmarkFetchResult, XClient
from ..repositories.posts import PostsRepository
from ..repositories.sync_state import SyncState, SyncStateRepository


# D-05: 800 bookmark limit warning threshold
WARNING_THRESHOLD = 750
API_LIMIT = 800


@dataclass
class SyncResult:
    """Result of a sync operation.

    Attributes:
        total_fetched: Total bookmarks fetched from API.
        new_count: New bookmarks added to database.
        updated_count: Existing bookmarks updated.
        error_count: Errors encountered during sync.
        rate_limit_waits: Number of times rate limit wait occurred.
        is_complete: True if sync finished all pages.
        warnings: List of warning messages (e.g., 800 limit warning).
    """
    total_fetched: int = 0
    new_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    rate_limit_waits: int = 0
    is_complete: bool = True
    warnings: list[str] = field(default_factory=list)


class SyncService:
    """Orchestrates bookmark sync from X API to SQLite.

    Features:
    - Full sync (first run): Fetches all available bookmarks
    - Incremental sync (subsequent): Only fetches new bookmarks
    - Rate limit handling: Auto-wait when approaching limit
    - Resume capability: Persists pagination token
    - 800 limit warning: Alerts when approaching API limit
    """

    def __init__(
        self,
        access_token: str,
        conn: sqlite3.Connection,
        on_rate_limit: Optional[Callable[[float], None]] = None,
        on_warning: Optional[Callable[[str], None]] = None,
        on_progress: Optional[Callable[[int], None]] = None,
    ):
        """Initialize sync service.

        Args:
            access_token: OAuth 2.0 access token.
            conn: SQLite connection.
            on_rate_limit: Callback for rate limit wait (receives wait_seconds).
            on_warning: Callback for warnings (receives warning message).
            on_progress: Callback for progress updates (receives fetched count).
        """
        self._access_token = access_token
        self._client: Optional[XClient] = None
        self._posts_repo = PostsRepository(conn)
        self._sync_state_repo = SyncStateRepository(conn)
        self._conn = conn

        self._on_rate_limit = on_rate_limit
        self._on_warning = on_warning
        self._on_progress = on_progress

    def _create_client(self) -> XClient:
        """Create XClient instance. Override in tests for mocking."""
        return XClient(self._access_token)

    def sync(self, limit: Optional[int] = None) -> SyncResult:
        """Sync bookmarks from X API to database.

        Performs incremental sync if last_sync_bookmark_id exists,
        otherwise performs full sync.

        Args:
            limit: Maximum number of bookmarks to fetch. If None, fetches all.

        Returns:
            SyncResult with counts and status.
        """
        # Create client if not already created
        if self._client is None:
            self._client = self._create_client()

        state = self._sync_state_repo.get_state()

        # Determine sync mode
        if state.last_sync_bookmark_id:
            return self._incremental_sync(state, limit=limit)
        else:
            return self._full_sync(state, limit=limit)

    def _full_sync(self, state: SyncState, limit: Optional[int] = None) -> SyncResult:
        """Perform full sync (first time or reset).

        Fetches all bookmarks, stores them, and updates sync state.
        """
        result = SyncResult()
        pagination_token = state.pagination_token  # Resume if interrupted
        highest_id: Optional[str] = None
        is_first_page = True

        while True:
            # Fetch page
            fetch_result = self._fetch_with_rate_limit(pagination_token)

            if not fetch_result.tweets:
                break

            # Process and store tweets
            count_before = self._posts_repo.count()
            self._store_tweets(fetch_result)
            count_after = self._posts_repo.count()

            result.total_fetched += len(fetch_result.tweets)
            result.new_count += (count_after - count_before)

            # Check if we've reached the limit
            if limit is not None and result.total_fetched >= limit:
                result.is_complete = True
                break

            # Track highest ID for incremental sync (first tweet of first page is newest)
            if is_first_page and fetch_result.tweets:
                highest_id = str(fetch_result.tweets[0].id)
                is_first_page = False

            # Progress callback
            if self._on_progress:
                self._on_progress(result.total_fetched)

            # D-05: Check for 800 limit warning
            if result.total_fetched >= WARNING_THRESHOLD:
                warning = f"Approaching API limit: {result.total_fetched}/{API_LIMIT} bookmarks"
                result.warnings.append(warning)
                if self._on_warning:
                    self._on_warning(warning)

            # Check for more pages
            if fetch_result.next_token:
                pagination_token = fetch_result.next_token
                # D-03: Persist pagination token for resume
                self._sync_state_repo.update_state(pagination_token=pagination_token)
            else:
                result.is_complete = True
                break

        # Update final sync state
        self._sync_state_repo.update_state(
            last_sync_bookmark_id=highest_id,
            reset_pagination=True,
        )
        self._sync_state_repo.set_total_count(result.total_fetched)

        return result

    def _incremental_sync(self, state: SyncState, limit: Optional[int] = None) -> SyncResult:
        """Perform incremental sync.

        D-02: Only fetches bookmarks newer than last_sync_bookmark_id.
        Stops when reaching the last known bookmark.

        Args:
            state: Current sync state.
            limit: Maximum number of bookmarks to fetch. If None, fetches all.
        """
        result = SyncResult()
        pagination_token = state.pagination_token
        stop_id = state.last_sync_bookmark_id
        new_highest_id: Optional[str] = None

        while True:
            fetch_result = self._fetch_with_rate_limit(pagination_token)

            if not fetch_result.tweets:
                break

            # Process tweets until we hit the stop ID
            for tweet in fetch_result.tweets:
                tweet_id = str(tweet.id)

                # D-02: Stop when we reach the last known bookmark
                if tweet_id == stop_id:
                    result.is_complete = True
                    # Update sync state with new highest ID
                    if new_highest_id:
                        self._sync_state_repo.update_state(
                            last_sync_bookmark_id=new_highest_id,
                            reset_pagination=True,
                        )
                    return result

                # Store this tweet
                self._store_tweet(tweet, fetch_result)
                result.total_fetched += 1

                # Check if we've reached the limit
                if limit is not None and result.total_fetched >= limit:
                    result.is_complete = True
                    # Update sync state with new highest ID
                    if new_highest_id:
                        self._sync_state_repo.update_state(
                            last_sync_bookmark_id=new_highest_id,
                            reset_pagination=True,
                        )
                    return result

                # Track first (newest) tweet ID as potential new highest
                if new_highest_id is None:
                    new_highest_id = tweet_id

            # Progress callback
            if self._on_progress:
                self._on_progress(result.total_fetched)

            # Check for more pages
            if fetch_result.next_token:
                pagination_token = fetch_result.next_token
                self._sync_state_repo.update_state(pagination_token=pagination_token)
            else:
                break

        # Update sync state
        if new_highest_id:
            self._sync_state_repo.update_state(
                last_sync_bookmark_id=new_highest_id,
                reset_pagination=True,
            )

        result.is_complete = True
        return result

    def _fetch_with_rate_limit(
        self,
        pagination_token: Optional[str] = None
    ) -> BookmarkFetchResult:
        """Fetch bookmarks with rate limit handling.

        D-03: Auto-wait when approaching rate limit.
        """
        result = self._client.fetch_bookmarks(
            max_results=50,  # X API bug: max_results=100 doesn't return next_token
            pagination_token=pagination_token,
        )

        # D-03: Check rate limit and wait if needed
        if result.rate_limit.remaining <= 5:
            wait_seconds = result.rate_limit.wait_seconds
            if self._on_rate_limit:
                self._on_rate_limit(wait_seconds)

            # Wait for rate limit reset
            time.sleep(wait_seconds + 1)

        return result

    def _store_tweets(self, fetch_result: BookmarkFetchResult) -> None:
        """Store all tweets from fetch result."""
        for tweet in fetch_result.tweets:
            self._store_tweet(tweet, fetch_result)

    def _store_tweet(self, tweet: Any, fetch_result: BookmarkFetchResult) -> None:
        """Store a single tweet with author and media info."""
        author = fetch_result.users.get(tweet.author_id)
        media_keys = []
        if hasattr(tweet, 'attachments') and tweet.attachments:
            media_keys = getattr(tweet.attachments, 'media_keys', [])

        media = []
        for mk in media_keys:
            if mk in fetch_result.media:
                m = fetch_result.media[mk]
                if hasattr(m, 'url'):
                    media.append(m)

        # Extract URLs from tweet entities
        link_urls = self._extract_links(tweet)

        post = {
            'x_post_id': str(tweet.id),
            'created_at': tweet.created_at.isoformat() if hasattr(tweet, 'created_at') and tweet.created_at else None,
            'text': tweet.text,
            'author_id': str(tweet.author_id) if tweet.author_id else '',
            'author_username': author.username if author else '',
            'author_display_name': author.name if author else '',
            'media_urls': [m.url for m in media if hasattr(m, 'url')],
            'link_urls': link_urls,
            'bookmarked_at': None,  # X API doesn't provide bookmark timestamp
        }

        self._posts_repo.upsert_post(post)

    def _extract_links(self, tweet: Any) -> list[str]:
        """Extract URLs from tweet entities."""
        urls = []
        if hasattr(tweet, 'entities') and tweet.entities and 'urls' in tweet.entities:
            for url_obj in tweet.entities['urls']:
                url = url_obj.get('expanded_url') or url_obj.get('url')
                if url:
                    urls.append(url)
        return urls