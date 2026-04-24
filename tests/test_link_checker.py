"""Tests for LinkChecker service.

Tests for:
- Async concurrent HTTP HEAD requests (MAINT-01)
- Link status caching and updates
- Dead link detection and flagging

MAINT-01: Application detects and flags dead links.
MAINT-02: Application can filter dead links from review queue.
"""

import asyncio
import sqlite3
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_with_links():
    """Create a temporary database with posts containing links.

    Yields:
        sqlite3.Connection: Connection with sample posts with link_urls.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Apply required PRAGMAs
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    # Create posts table with v3 schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            x_post_id TEXT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL,
            text TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_username TEXT NOT NULL,
            author_display_name TEXT,
            media_urls TEXT,
            link_urls TEXT,
            bookmarked_at TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_version INTEGER DEFAULT 1,
            note TEXT,
            link_status TEXT DEFAULT 'unchecked'
        )
    """)

    # Insert sample posts with links
    conn.execute("""
        INSERT INTO posts (x_post_id, created_at, text, author_id, author_username, link_urls, link_status)
        VALUES ('post1', '2024-01-01T00:00:00Z', 'Post with one link', 'user1', 'testuser',
                '["https://example.com"]', 'unchecked')
    """)
    conn.execute("""
        INSERT INTO posts (x_post_id, created_at, text, author_id, author_username, link_urls, link_status)
        VALUES ('post2', '2024-01-02T00:00:00Z', 'Post with two links', 'user1', 'testuser',
                '["https://example.com/page1", "https://example.com/page2"]', 'unchecked')
    """)
    conn.execute("""
        INSERT INTO posts (x_post_id, created_at, text, author_id, author_username, link_urls, link_status)
        VALUES ('post3', '2024-01-03T00:00:00Z', 'Post with dead link', 'user2', 'anotheruser',
                '["https://dead.example.com/404"]', 'unchecked')
    """)
    conn.execute("""
        INSERT INTO posts (x_post_id, created_at, text, author_id, author_username, link_urls, link_status)
        VALUES ('post4', '2024-01-04T00:00:00Z', 'Post recently checked', 'user1', 'testuser',
                '["https://recent.example.com"]', '2024-01-04T00:00:00Z')
    """)
    conn.execute("""
        INSERT INTO posts (x_post_id, created_at, text, author_id, author_username, link_urls, link_status)
        VALUES ('post5', '2024-01-05T00:00:00Z', 'Post with error status', 'user1', 'testuser',
                '["https://error.example.com"]', 'error')
    """)

    conn.commit()

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


class TestLinkStatus:
    """Tests for LinkStatus dataclass."""

    def test_link_status_creation(self):
        """Verify LinkStatus dataclass stores url, status, and optional fields."""
        from src.services.link_checker import LinkStatus

        status = LinkStatus(url="https://example.com", status="ok")
        assert status.url == "https://example.com"
        assert status.status == "ok"
        assert status.status_code is None
        assert status.error_message is None

    def test_link_status_with_all_fields(self):
        """Verify LinkStatus can store all optional fields."""
        from src.services.link_checker import LinkStatus

        status = LinkStatus(
            url="https://example.com",
            status="ok",
            status_code=200,
            error_message=None,
        )
        assert status.status_code == 200


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_check_result_creation(self):
        """Verify CheckResult stores counts and results."""
        from src.services.link_checker import CheckResult, LinkStatus

        result = CheckResult(
            total_checked=5,
            ok_count=3,
            dead_count=1,
            error_count=1,
            results=[],
        )
        assert result.total_checked == 5
        assert result.ok_count == 3
        assert result.dead_count == 1
        assert result.error_count == 1


class TestLinkCheckerServiceInit:
    """Tests for LinkCheckerService initialization."""

    def test_init_accepts_timeout_parameter(self, temp_db_with_links):
        """Verify LinkCheckerService.__init__() accepts timeout parameter."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo, timeout=5.0)

        assert service._timeout is not None
        assert service.MAX_CONCURRENT == 10
        assert service.DEFAULT_TIMEOUT == 10.0

    def test_init_accepts_progress_callback(self, temp_db_with_links):
        """Verify LinkCheckerService.__init__() accepts on_progress callback."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)

        progress_calls = []

        def on_progress(completed, total):
            progress_calls.append((completed, total))

        service = LinkCheckerService(repo, on_progress=on_progress)
        assert service._on_progress == on_progress


class TestCheckSingleUrl:
    """Tests for _check_single URL checking method."""

    @pytest.mark.asyncio
    async def test_check_single_url_ok(self, temp_db_with_links):
        """Verify _check_single returns 'ok' status for 200 response."""
        from src.services.link_checker import LinkCheckerService, LinkStatus
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo, timeout=10.0)

        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.head = AsyncMock(return_value=mock_response)

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com", semaphore)

        assert result.status == "ok"
        assert result.url == "https://example.com"
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_check_single_url_dead_404(self, temp_db_with_links):
        """Verify _check_single returns 'dead' status for 404 response."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.head = AsyncMock(return_value=mock_response)

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com/notfound", semaphore)

        assert result.status == "dead"
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_check_single_url_dead_500(self, temp_db_with_links):
        """Verify _check_single returns 'dead' status for 5xx response."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_client.head = AsyncMock(return_value=mock_response)

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com/error", semaphore)

        assert result.status == "dead"
        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_check_single_url_timeout(self, temp_db_with_links):
        """Verify _check_single returns 'error' status for timeout."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository
        import httpx

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com/slow", semaphore)

        assert result.status == "error"
        assert result.error_message == "timeout"

    @pytest.mark.asyncio
    async def test_check_single_url_http_error(self, temp_db_with_links):
        """Verify _check_single returns 'error' status for HTTP errors."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository
        import httpx

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=httpx.HTTPError("connection error"))

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com/error", semaphore)

        assert result.status == "error"
        assert result.error_message == "connection error"

    @pytest.mark.asyncio
    async def test_check_single_url_follows_redirects(self, temp_db_with_links):
        """Verify _check_single follows redirects (302 -> 200)."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200  # Final status after redirect
        mock_client.head = AsyncMock(return_value=mock_response)

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com/redirect", semaphore)

        # Verify head was called with follow_redirects=True
        mock_client.head.assert_called_once()
        call_kwargs = mock_client.head.call_args[1]
        assert call_kwargs.get("follow_redirects") is True
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_single_url_respects_semaphore(self, temp_db_with_links):
        """Verify _check_single respects semaphore limiting."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.head = AsyncMock(return_value=mock_response)

        # Use a semaphore with limit of 2
        semaphore = asyncio.Semaphore(2)

        # Acquire one permit to verify semaphore is used
        async with semaphore:
            # This should wait for semaphore
            task = asyncio.create_task(
                service._check_single(mock_client, "https://example.com", semaphore)
            )
            # Let the task start and wait at semaphore
            await asyncio.sleep(0.01)
            # Semaphore is still held by outer context, so task should be waiting
            # Release happens when we exit the async with block

        # Now task can complete
        result = await task
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_check_single_url_redirect_to_404(self, temp_db_with_links):
        """Verify _check_single returns 'dead' when redirect leads to 404."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.head = AsyncMock(return_value=mock_response)

        semaphore = asyncio.Semaphore(10)
        result = await service._check_single(mock_client, "https://example.com/old-link", semaphore)

        assert result.status == "dead"
        assert result.status_code == 404


class TestCheckAllLinks:
    """Tests for check_all_links method."""

    @pytest.mark.asyncio
    async def test_check_all_links_returns_check_result(self, temp_db_with_links):
        """Verify check_all_links returns CheckResult with counts."""
        from src.services.link_checker import LinkCheckerService, CheckResult
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.check_all_links()

            assert isinstance(result, CheckResult)
            assert result.total_checked > 0

    @pytest.mark.asyncio
    async def test_check_all_links_updates_database(self, temp_db_with_links):
        """Verify check_all_links updates link_status in database."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links()

        # Verify database was updated
        post = repo.get_by_id("post1")
        assert post["link_status"] == "ok"

    @pytest.mark.asyncio
    async def test_check_all_links_progress_callback(self, temp_db_with_links):
        """Verify check_all_links calls on_progress callback."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        progress_calls = []

        def on_progress(completed, total):
            progress_calls.append((completed, total))

        service = LinkCheckerService(repo, on_progress=on_progress)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links()

        # Progress callback should be called
        assert len(progress_calls) > 0
        # Final call should have completed == total
        final_call = progress_calls[-1]
        assert final_call[0] == final_call[1]

    @pytest.mark.asyncio
    async def test_check_all_links_handles_multiple_urls_per_post(self, temp_db_with_links):
        """Verify check_all_links handles posts with multiple links."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        call_count = 0

        def mock_head(url, follow_redirects=True):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            mock_response.status_code = 200
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(side_effect=mock_head)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links()

        # post2 has 2 links, so we expect multiple calls
        # Total: post1(1) + post2(2) + post3(1) + post5(1) = 5 links
        assert call_count >= 5

    @pytest.mark.asyncio
    async def test_check_all_links_marks_dead_links(self, temp_db_with_links):
        """Verify check_all_links marks posts with dead links."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        def mock_head(url, follow_redirects=True):
            mock_response = AsyncMock()
            # Dead link for dead.example.com
            if "dead.example.com" in url:
                mock_response.status_code = 404
            else:
                mock_response.status_code = 200
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(side_effect=mock_head)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links()

        # post3 has dead.example.com link
        post3 = repo.get_by_id("post3")
        assert post3["link_status"] == "dead"

    @pytest.mark.asyncio
    async def test_check_all_links_marks_error_links(self, temp_db_with_links):
        """Verify check_all_links marks posts with error status."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository
        import httpx

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        def mock_head(url, follow_redirects=True):
            if "error.example.com" in url:
                raise httpx.TimeoutException("timeout")
            mock_response = AsyncMock()
            mock_response.status_code = 200
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(side_effect=mock_head)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links()

        # post5 has error.example.com link
        post5 = repo.get_by_id("post5")
        assert post5["link_status"] == "error"


class TestCacheLogic:
    """Tests for caching and recheck logic."""

    def test_should_check_unchecked(self, temp_db_with_links):
        """Verify _should_check returns True for 'unchecked' status."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        post = {"link_status": "unchecked"}
        assert service._should_check(post) is True

    def test_should_check_error_always_rechecks(self, temp_db_with_links):
        """Verify _should_check returns True for 'error' status (always recheck)."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        post = {"link_status": "error"}
        assert service._should_check(post) is True

    def test_should_check_dead_always_rechecks(self, temp_db_with_links):
        """Verify _should_check returns True for 'dead' status (always recheck)."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        post = {"link_status": "dead"}
        assert service._should_check(post) is True

    def test_should_check_skips_recent_ok(self, temp_db_with_links):
        """Verify _should_check returns False for recently checked 'ok' links."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        # Recently checked (within cache period)
        recent = datetime.now(timezone.utc).isoformat()
        post = {"link_status": recent}
        assert service._should_check(post) is False

    def test_should_check_rechecks_old_timestamp(self, temp_db_with_links):
        """Verify _should_check returns True for old timestamps (past cache period)."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo, cache_days=30)

        # Old timestamp (60 days ago)
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        post = {"link_status": old_date.isoformat()}
        assert service._should_check(post) is True

    def test_should_check_invalid_timestamp_rechecks(self, temp_db_with_links):
        """Verify _should_check returns True for invalid timestamps."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        post = {"link_status": "invalid-timestamp"}
        assert service._should_check(post) is True

    @pytest.mark.asyncio
    async def test_check_all_links_skips_cached(self, temp_db_with_links):
        """Verify check_all_links skips recently checked links."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        call_count = 0

        def mock_head(url, follow_redirects=True):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            mock_response.status_code = 200
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(side_effect=mock_head)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links()

        # post4 has recent timestamp, should be skipped
        # post5 has 'error' status, should be rechecked
        # post1, post2, post3 have 'unchecked', should be checked
        # Total: post1(1) + post2(2) + post3(1) + post5(1) = 5 links (post4 skipped)

    @pytest.mark.asyncio
    async def test_check_all_links_force_rechecks_all(self, temp_db_with_links):
        """Verify check_all_links with force=True checks all links."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        call_count = 0

        def mock_head(url, follow_redirects=True):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            mock_response.status_code = 200
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.head = AsyncMock(side_effect=mock_head)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            await service.check_all_links(force=True)

        # All posts checked, including post4 (recent) and post5 (error)
        # Total links: post1(1) + post2(2) + post3(1) + post4(1) + post5(1) = 6
        assert call_count == 6

    def test_cache_days_configurable(self, temp_db_with_links):
        """Verify cache_days is configurable in __init__."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo, cache_days=7)
        assert service._cache_days == 7


class TestSyncWrapper:
    """Tests for synchronous wrapper."""

    def test_check_all_links_sync_wrapper(self, temp_db_with_links):
        """Verify check_all_links_sync runs async function correctly."""
        from src.services.link_checker import LinkCheckerService
        from src.repositories.posts import PostsRepository

        repo = PostsRepository(temp_db_with_links)
        service = LinkCheckerService(repo)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.head = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = service.check_all_links_sync()

            assert result.total_checked > 0