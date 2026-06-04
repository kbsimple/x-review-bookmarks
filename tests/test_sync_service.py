"""Tests for SyncService - bookmark sync orchestration.

Tests verify:
- Full sync (first run): Fetches all available bookmarks
- Incremental sync: Only fetches new bookmarks
- Rate limit handling: Auto-wait when approaching limit
- 800 limit warning: Alerts when approaching API limit
- Resume capability: Persists pagination token

DATA-01: Fetch bookmarked posts from X API.
DATA-04: Handle X API rate limits.
DATA-05: Handle 800 bookmark API limit.
STOR-03: Incremental sync (only fetch new bookmarks).
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

from src.api.x_client import BookmarkFetchResult, RateLimitInfo
from src.db import init_database
from src.repositories import PostsRepository, SyncStateRepository
from src.services import SyncService, SyncResult


# Helper to create mock tweet objects
@dataclass
class MockTweet:
    """Mock Tweet object mimicking tweepy Tweet structure."""
    id: str
    text: str
    author_id: str
    created_at: Any = None
    entities: dict = None
    attachments: Any = None

    def __post_init__(self):
        if self.entities is None:
            self.entities = {}
        if self.created_at is None:
            self.created_at = MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z")


@dataclass
class MockUser:
    """Mock User object mimicking tweepy User structure."""
    id: str
    username: str
    name: str


@pytest.fixture
def db_with_schema():
    """Create a database with schema for testing sync operations."""
    conn = init_database(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def posts_repo(db_with_schema):
    """Create PostsRepository with test database."""
    return PostsRepository(db_with_schema)


@pytest.fixture
def sync_state_repo(db_with_schema):
    """Create SyncStateRepository with test database."""
    return SyncStateRepository(db_with_schema)


class TestFullSync:
    """Tests for full sync (first run, no previous sync state)."""

    def test_full_sync_fetches_all(self, db_with_schema, posts_repo, sync_state_repo):
        """Full sync should fetch all pages and store all tweets."""
        # Create mock tweets for 2 pages
        page1_tweets = [
            MockTweet(id="100", text="Tweet 100", author_id="user1"),
            MockTweet(id="99", text="Tweet 99", author_id="user1"),
        ]
        page2_tweets = [
            MockTweet(id="98", text="Tweet 98", author_id="user2"),
            MockTweet(id="97", text="Tweet 97", author_id="user2"),
        ]

        users = {
            "user1": MockUser(id="user1", username="user1_handle", name="User One"),
            "user2": MockUser(id="user2", username="user2_handle", name="User Two"),
        }

        # Mock XClient.fetch_bookmarks to return 2 pages
        call_count = [0]

        def mock_fetch(max_results=100, pagination_token=None):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: return page 1 with next_token
                return BookmarkFetchResult(
                    tweets=page1_tweets,
                    users=users,
                    media={},
                    next_token="token_page2",
                    result_count=2,
                    rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
                )
            else:
                # Second call: return page 2 without next_token (end)
                return BookmarkFetchResult(
                    tweets=page2_tweets,
                    users=users,
                    media={},
                    next_token=None,
                    result_count=2,
                    rate_limit=RateLimitInfo(remaining=179, reset_at=time.time() + 900),
                )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        # Verify all tweets fetched
        assert result.total_fetched == 4
        assert result.is_complete is True

        # Verify all stored in database
        assert posts_repo.count() == 4

        # Verify sync state updated
        state = sync_state_repo.get_state()
        assert state.last_sync_bookmark_id == "100"  # First (newest) tweet

    def test_full_sync_empty_response(self, db_with_schema, posts_repo):
        """Full sync with no bookmarks should complete gracefully."""
        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=[],
                users={},
                media={},
                next_token=None,
                result_count=0,
                rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        assert result.total_fetched == 0
        assert result.is_complete is True
        assert posts_repo.count() == 0


class TestIncrementalSync:
    """Tests for incremental sync (subsequent runs)."""

    def test_incremental_sync_stops_at_known_id(self, db_with_schema, posts_repo, sync_state_repo):
        """Incremental sync should stop when reaching last known bookmark ID."""
        # Set up existing sync state with last_sync_bookmark_id
        sync_state_repo.update_state(last_sync_bookmark_id="100")

        # Add some existing posts (simulating previous sync)
        posts_repo.upsert_post({
            'x_post_id': '100',
            'created_at': '2024-01-01T00:00:00Z',
            'text': 'Old tweet',
            'author_id': 'user1',
            'author_username': 'user1_handle',
        })
        posts_repo.upsert_post({
            'x_post_id': '99',
            'created_at': '2024-01-01T00:00:00Z',
            'text': 'Old tweet 2',
            'author_id': 'user1',
            'author_username': 'user1_handle',
        })

        # Create mock tweets: new ones + the known stop ID
        new_tweets = [
            MockTweet(id="102", text="New tweet 102", author_id="user1"),
            MockTweet(id="101", text="New tweet 101", author_id="user1"),
            MockTweet(id="100", text="Tweet 100 (stop here)", author_id="user1"),  # Stop ID
        ]

        users = {
            "user1": MockUser(id="user1", username="user1_handle", name="User One"),
        }

        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=new_tweets,
                users=users,
                media={},
                next_token=None,
                result_count=3,
                rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        # Should only fetch new tweets (102, 101), stop at 100
        assert result.total_fetched == 2
        assert result.is_complete is True

        # Verify new tweets stored
        assert posts_repo.count() == 4  # 2 existing + 2 new

    def test_incremental_sync_no_new_tweets(self, db_with_schema, posts_repo, sync_state_repo):
        """Incremental sync with no new tweets should return empty result."""
        sync_state_repo.update_state(last_sync_bookmark_id="100")

        # Return only tweets older than or equal to stop ID
        tweets = [
            MockTweet(id="100", text="Already synced", author_id="user1"),
            MockTweet(id="99", text="Old tweet", author_id="user1"),
        ]

        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=tweets,
                users=users,
                media={},
                next_token=None,
                result_count=2,
                rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        # Should stop immediately at first tweet
        assert result.total_fetched == 0


class TestRateLimitHandling:
    """Tests for rate limit auto-wait behavior."""

    def test_rate_limit_auto_waits(self, db_with_schema):
        """Sync should auto-wait when rate limit remaining <= 5."""
        tweets = [MockTweet(id="100", text="Tweet", author_id="user1")]
        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        rate_limit_calls = []

        def on_rate_limit(wait_seconds):
            rate_limit_calls.append(wait_seconds)

        # Create a rate limit that will trigger wait
        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=tweets,
                users=users,
                media={},
                next_token=None,
                result_count=1,
                rate_limit=RateLimitInfo(remaining=3, reset_at=time.time() + 60),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            # Patch time.sleep to avoid actual waiting
            with patch('time.sleep') as mock_sleep:
                sync_service = SyncService(
                    "test_token",
                    db_with_schema,
                    on_rate_limit=on_rate_limit,
                )
                result = sync_service.sync()

        # Verify rate limit callback was called
        assert len(rate_limit_calls) == 1
        assert rate_limit_calls[0] > 0

        # Verify sleep was called
        mock_sleep.assert_called()

    def test_rate_limit_no_wait_when_high_remaining(self, db_with_schema):
        """Sync should NOT wait when rate limit remaining > 5."""
        tweets = [MockTweet(id="100", text="Tweet", author_id="user1")]
        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        rate_limit_calls = []

        def on_rate_limit(wait_seconds):
            rate_limit_calls.append(wait_seconds)

        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=tweets,
                users=users,
                media={},
                next_token=None,
                result_count=1,
                rate_limit=RateLimitInfo(remaining=100, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            with patch('time.sleep') as mock_sleep:
                sync_service = SyncService(
                    "test_token",
                    db_with_schema,
                    on_rate_limit=on_rate_limit,
                )
                result = sync_service.sync()

        # Verify rate limit callback was NOT called
        assert len(rate_limit_calls) == 0
        mock_sleep.assert_not_called()


class Test800LimitWarning:
    """Tests for 800 bookmark API limit warning."""

    def test_800_limit_warning_triggered(self, db_with_schema):
        """Warning should trigger when total fetched > 750."""
        warnings = []

        def on_warning(message):
            warnings.append(message)

        # Create more than 750 tweets (mock as single large batch)
        tweets = [
            MockTweet(id=str(800 - i), text=f"Tweet {800-i}", author_id="user1")
            for i in range(760)
        ]
        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=tweets,
                users=users,
                media={},
                next_token=None,
                result_count=760,
                rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService(
                "test_token",
                db_with_schema,
                on_warning=on_warning,
            )
            result = sync_service.sync()

        # Warning should be in result
        assert len(result.warnings) > 0
        assert "800" in result.warnings[0] or "750" in result.warnings[0]

    def test_no_warning_below_threshold(self, db_with_schema):
        """No warning when total fetched < 750."""
        warnings = []

        def on_warning(message):
            warnings.append(message)

        tweets = [MockTweet(id="100", text="Tweet", author_id="user1")]
        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=tweets,
                users=users,
                media={},
                next_token=None,
                result_count=1,
                rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService(
                "test_token",
                db_with_schema,
                on_warning=on_warning,
            )
            result = sync_service.sync()

        assert len(warnings) == 0
        assert len(result.warnings) == 0


class TestPaginationPersistence:
    """Tests for pagination token persistence."""

    def test_pagination_persists_during_sync(self, db_with_schema, sync_state_repo):
        """Pagination token should be persisted after each page for resume."""
        page1_tweets = [MockTweet(id="100", text="Tweet 100", author_id="user1")]
        page2_tweets = [MockTweet(id="99", text="Tweet 99", author_id="user1")]

        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        call_count = [0]
        pagination_tokens_saved = []

        # Track when pagination tokens are saved
        original_update = sync_state_repo.update_state

        def track_update(*args, **kwargs):
            if 'pagination_token' in kwargs and kwargs['pagination_token']:
                pagination_tokens_saved.append(kwargs['pagination_token'])
            return original_update(*args, **kwargs)

        def mock_fetch(max_results=100, pagination_token=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return BookmarkFetchResult(
                    tweets=page1_tweets,
                    users=users,
                    media={},
                    next_token="token_page2",
                    result_count=1,
                    rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
                )
            else:
                return BookmarkFetchResult(
                    tweets=page2_tweets,
                    users=users,
                    media={},
                    next_token=None,
                    result_count=1,
                    rate_limit=RateLimitInfo(remaining=179, reset_at=time.time() + 900),
                )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            with patch.object(sync_state_repo, 'update_state', track_update):
                sync_service = SyncService("test_token", db_with_schema)
                sync_service._sync_state_repo = sync_state_repo
                result = sync_service.sync()

        # Verify pagination token was saved during sync
        assert "token_page2" in pagination_tokens_saved

    def test_pagination_resets_after_complete(self, db_with_schema, sync_state_repo):
        """Pagination token should be cleared after successful sync completion."""
        tweets = [MockTweet(id="100", text="Tweet 100", author_id="user1")]
        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        def mock_fetch(max_results=100, pagination_token=None):
            return BookmarkFetchResult(
                tweets=tweets,
                users=users,
                media={},
                next_token=None,
                result_count=1,
                rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
            )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        # After complete sync, pagination token should be None
        state = sync_state_repo.get_state()
        assert state.pagination_token is None


class TestProgressCallback:
    """Tests for progress callback during sync."""

    def test_progress_callback_called(self, db_with_schema):
        """Progress callback should be called with fetched count."""
        progress_updates = []

        def on_progress(count):
            progress_updates.append(count)

        page1_tweets = [
            MockTweet(id="100", text="Tweet 100", author_id="user1"),
            MockTweet(id="99", text="Tweet 99", author_id="user1"),
        ]
        page2_tweets = [
            MockTweet(id="98", text="Tweet 98", author_id="user1"),
        ]

        users = {"user1": MockUser(id="user1", username="user1_handle", name="User One")}

        call_count = [0]

        def mock_fetch(max_results=100, pagination_token=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return BookmarkFetchResult(
                    tweets=page1_tweets,
                    users=users,
                    media={},
                    next_token="token_page2",
                    result_count=2,
                    rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
                )
            else:
                return BookmarkFetchResult(
                    tweets=page2_tweets,
                    users=users,
                    media={},
                    next_token=None,
                    result_count=1,
                    rate_limit=RateLimitInfo(remaining=179, reset_at=time.time() + 900),
                )

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService(
                "test_token",
                db_with_schema,
                on_progress=on_progress,
            )
            result = sync_service.sync()

        # Progress should be updated for each page
        assert len(progress_updates) >= 1
        # Final count should be total fetched
        assert progress_updates[-1] == 3


class TestStoreTweet:
    """Tests for tweet storage with author and media info."""

    def test_store_tweet_with_author(self, db_with_schema, posts_repo):
        """Tweet should be stored with author information."""
        tweet = MockTweet(id="100", text="Hello world", author_id="user1")
        users = {"user1": MockUser(id="user1", username="testuser", name="Test User")}

        fetch_result = BookmarkFetchResult(
            tweets=[tweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        # Verify stored with author info
        stored = posts_repo.get_by_id("100")
        assert stored is not None
        assert stored['text'] == "Hello world"
        assert stored['author_username'] == "testuser"
        assert stored['author_display_name'] == "Test User"

    def test_store_tweet_with_links(self, db_with_schema, posts_repo):
        """Tweet should be stored with extracted link URLs."""
        tweet = MockTweet(
            id="100",
            text="Check this out!",
            author_id="user1",
            entities={'urls': [{'url': 'https://t.co/abc', 'expanded_url': 'https://example.com'}]}
        )
        users = {"user1": MockUser(id="user1", username="testuser", name="Test User")}

        fetch_result = BookmarkFetchResult(
            tweets=[tweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            result = sync_service.sync()

        # Verify stored with links
        stored = posts_repo.get_by_id("100")
        assert stored is not None
        assert 'https://example.com' in stored['link_urls']


class TestEmbeddedPostsSync:
    """Tests for embedded post handling during sync.

    STR-02: Posts table gains post_type column for retweet/quote/original distinction.
    STR-03: Unavailable originals marked and stored for graceful handling.
    """

    def test_store_tweet_sets_post_type_original(self, db_with_schema, posts_repo):
        """Verify original posts have post_type='original' and no embedded_post_id.

        STR-02: Original posts have post_type='original'.
        """
        from src.services.sync import SyncService

        # Tweet without referenced_tweets is an original post
        tweet = MockTweet(id="100", text="Original post content", author_id="user1")
        users = {"user1": MockUser(id="user1", username="testuser", name="Test User")}

        fetch_result = BookmarkFetchResult(
            tweets=[tweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            sync_service.sync()

        # Verify post_type and embedded_post_id
        stored = posts_repo.get_by_id("100")
        assert stored is not None
        assert stored.get("post_type") == "original"
        assert stored.get("embedded_post_id") is None

    def test_store_tweet_sets_post_type_retweet(self, db_with_schema, posts_repo):
        """Verify retweets have post_type='retweet' and embedded_post_id set.

        STR-02: Retweets have post_type='retweet' and reference embedded post.
        """
        from src.services.sync import SyncService

        # Create a retweet with referenced_tweets
        retweet = MagicMock()
        retweet.id = "200"
        retweet.text = "RT @original_author: This is being retweeted"
        retweet.author_id = "user2"
        retweet.referenced_tweets = [MagicMock(type="retweeted", id="100")]

        # Original tweet in includes
        original_tweet = MagicMock()
        original_tweet.id = "100"
        original_tweet.text = "This is the original tweet content"
        original_tweet.author_id = "user1"
        original_tweet.created_at = MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z")

        users = {
            "user1": MockUser(id="user1", username="original_author", name="Original Author"),
            "user2": MockUser(id="user2", username="retweeter", name="Retweeter"),
        }

        fetch_result = BookmarkFetchResult(
            tweets=[retweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        # Add includes with referenced tweets
        fetch_result.includes = {"tweets": [original_tweet]}

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            sync_service.sync()

        # Verify retweet post
        stored = posts_repo.get_by_id("200")
        assert stored is not None
        assert stored.get("post_type") == "retweet"
        assert stored.get("embedded_post_id") == "100"

    def test_store_tweet_sets_post_type_quote(self, db_with_schema, posts_repo):
        """Verify quote tweets have post_type='quote' and embedded_post_id set.

        STR-02: Quote tweets have post_type='quote' and reference embedded post.
        """
        from src.services.sync import SyncService

        # Create a quote tweet with referenced_tweets
        quote_tweet = MagicMock()
        quote_tweet.id = "300"
        quote_tweet.text = "My commentary on this quote"
        quote_tweet.author_id = "user2"
        quote_tweet.referenced_tweets = [MagicMock(type="quoted", id="100")]

        # Original tweet in includes
        original_tweet = MagicMock()
        original_tweet.id = "100"
        original_tweet.text = "Original quoted content"
        original_tweet.author_id = "user1"
        original_tweet.created_at = MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z")

        users = {
            "user1": MockUser(id="user1", username="quoted_author", name="Quoted Author"),
            "user2": MockUser(id="user2", username="quoter", name="Quoter"),
        }

        fetch_result = BookmarkFetchResult(
            tweets=[quote_tweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        # Add includes with referenced tweets
        fetch_result.includes = {"tweets": [original_tweet]}

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            sync_service.sync()

        # Verify quote post
        stored = posts_repo.get_by_id("300")
        assert stored is not None
        assert stored.get("post_type") == "quote"
        assert stored.get("embedded_post_id") == "100"

    def test_store_tweet_handles_unavailable_embedded(self, db_with_schema, posts_repo):
        """Verify retweets with unavailable originals are handled gracefully.

        STR-03: Unavailable originals marked with available=False.
        """
        from src.services.sync import SyncService
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        embedded_repo = EmbeddedPostsRepository(db_with_schema)

        # Create a retweet where the original is not available
        retweet = MagicMock()
        retweet.id = "400"
        retweet.text = "RT @deleted_user: [unavailable]"
        retweet.author_id = "user2"
        retweet.referenced_tweets = [MagicMock(type="retweeted", id="deleted_100")]

        users = {
            "user2": MockUser(id="user2", username="retweeter", name="Retweeter"),
        }

        fetch_result = BookmarkFetchResult(
            tweets=[retweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        # No includes.tweets - original is unavailable
        fetch_result.includes = {"tweets": []}

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            sync_service.sync()

        # Verify embedded post created as unavailable
        embedded = embedded_repo.get_by_id("deleted_100")
        assert embedded is not None
        assert embedded.get("available") is False

        # Verify retweet still stored with correct post_type
        stored = posts_repo.get_by_id("400")
        assert stored is not None
        assert stored.get("post_type") == "retweet"
        assert stored.get("embedded_post_id") == "deleted_100"

    def test_store_tweet_stores_embedded_post_content(self, db_with_schema, posts_repo):
        """Verify embedded post content is stored for available originals.

        STR-01: Embedded posts stored in separate table with full content.
        """
        from src.services.sync import SyncService
        from src.repositories.embedded_posts import EmbeddedPostsRepository

        embedded_repo = EmbeddedPostsRepository(db_with_schema)

        # Create a retweet with available original
        retweet = MagicMock()
        retweet.id = "500"
        retweet.text = "RT @original_author"
        retweet.author_id = "user2"
        retweet.referenced_tweets = [MagicMock(type="retweeted", id="original_500")]

        # Original tweet available in includes
        original_tweet = MagicMock()
        original_tweet.id = "original_500"
        original_tweet.text = "This is the original content from the author"
        original_tweet.author_id = "user1"
        original_tweet.author_username = "original_author"
        original_tweet.author_name = "Original Author"
        original_tweet.created_at = MagicMock(isoformat=lambda: "2024-01-01T00:00:00Z")
        original_tweet.entities = {}

        users = {
            "user1": MockUser(id="user1", username="original_author", name="Original Author"),
            "user2": MockUser(id="user2", username="retweeter", name="Retweeter"),
        }

        fetch_result = BookmarkFetchResult(
            tweets=[retweet],
            users=users,
            media={},
            next_token=None,
            result_count=1,
            rate_limit=RateLimitInfo(remaining=180, reset_at=time.time() + 900),
        )

        # Add includes with referenced tweets
        fetch_result.includes = {"tweets": [original_tweet]}

        def mock_fetch(max_results=100, pagination_token=None):
            return fetch_result

        with patch.object(SyncService, '_create_client') as mock_client_factory:
            mock_client = MagicMock()
            mock_client.fetch_bookmarks = mock_fetch
            mock_client_factory.return_value = mock_client

            sync_service = SyncService("test_token", db_with_schema)
            sync_service.sync()

        # Verify embedded post stored with content
        embedded = embedded_repo.get_by_id("original_500")
        assert embedded is not None
        assert embedded.get("text") == "This is the original content from the author"
        assert embedded.get("author_username") == "original_author"
        assert embedded.get("available") is True

        # Verify retweet stored correctly
        stored = posts_repo.get_by_id("500")
        assert stored is not None
        assert stored.get("post_type") == "retweet"
        assert stored.get("embedded_post_id") == "original_500"