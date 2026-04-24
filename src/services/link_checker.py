"""LinkChecker service for async concurrent link status checking.

D-04: Async concurrent HTTP HEAD requests with semaphore limiting.
MAINT-01: Application detects and flags dead links in stored posts.
MAINT-02: Application can filter dead links from review queue.

Usage:
    from src.services import LinkCheckerService
    from src.repositories import PostsRepository
    from src.db import get_connection

    conn = get_connection()
    repo = PostsRepository(conn)
    service = LinkCheckerService(repo)

    # Check all links
    result = service.check_all_links_sync()
    print(f"Checked {result.total_checked} links: {result.ok_count} ok, {result.dead_count} dead")
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

import httpx


@dataclass
class LinkStatus:
    """Status of a single link check.

    Attributes:
        url: The URL that was checked.
        status: Status string: "ok", "dead", "error", or "unchecked".
        status_code: HTTP status code if available.
        error_message: Error message if status is "error".
    """

    url: str
    status: str  # "ok", "dead", "error", "unchecked"
    status_code: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class CheckResult:
    """Result of checking all links.

    Attributes:
        total_checked: Total number of links checked.
        ok_count: Number of links with "ok" status.
        dead_count: Number of links with "dead" status.
        error_count: Number of links with "error" status.
        results: List of (x_post_id, url, LinkStatus) tuples.
    """

    total_checked: int = 0
    ok_count: int = 0
    dead_count: int = 0
    error_count: int = 0
    results: list[tuple[str, str, LinkStatus]] = field(default_factory=list)


class LinkCheckerService:
    """Service for checking link status with concurrent HTTP requests.

    MAINT-01: Detects and flags dead links in stored posts.
    MAINT-02: Can filter dead links from review queue.

    Features:
    - Concurrent HTTP HEAD requests with semaphore limiting (max 10)
    - Timeout handling (default 10 seconds)
    - Caching to avoid re-checking recently verified links
    - Progress callbacks for CLI progress bars
    """

    MAX_CONCURRENT = 10
    DEFAULT_TIMEOUT = 10.0
    CACHE_DAYS = 30  # Recheck links older than 30 days

    def __init__(
        self,
        repo: Any,  # PostsRepository
        timeout: float = DEFAULT_TIMEOUT,
        cache_days: int = CACHE_DAYS,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ):
        """Initialize link checker.

        Args:
            repo: PostsRepository for database access.
            timeout: HTTP timeout in seconds.
            cache_days: Days to cache link status before rechecking.
            on_progress: Callback(completed, total) for progress updates.
        """
        self._repo = repo
        self._timeout = httpx.Timeout(timeout)
        self._cache_days = cache_days
        self._on_progress = on_progress

    def _should_check(self, post: dict[str, Any]) -> bool:
        """Determine if post's links need checking.

        Args:
            post: Post dict with link_status field.

        Returns:
            True if links should be checked, False to skip.
        """
        status = post.get("link_status", "unchecked")

        if status == "unchecked":
            return True

        if status in ("error", "dead"):
            return True  # Always recheck errors and dead links

        # Status is ISO timestamp - check age
        try:
            last_checked = datetime.fromisoformat(status.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - last_checked
            return age.days > self._cache_days
        except (ValueError, TypeError):
            return True  # Invalid timestamp, recheck

    async def _check_single(
        self,
        client: httpx.AsyncClient,
        url: str,
        semaphore: asyncio.Semaphore,
    ) -> LinkStatus:
        """Check a single URL with semaphore limiting.

        Args:
            client: httpx AsyncClient for making requests.
            url: URL to check.
            semaphore: Semaphore for concurrency limiting.

        Returns:
            LinkStatus with check result.
        """
        async with semaphore:
            try:
                response = await client.head(url, follow_redirects=True)
                if 200 <= response.status_code < 400:
                    return LinkStatus(
                        url=url, status="ok", status_code=response.status_code
                    )
                else:
                    return LinkStatus(
                        url=url, status="dead", status_code=response.status_code
                    )
            except httpx.TimeoutException:
                return LinkStatus(url=url, status="error", error_message="timeout")
            except httpx.HTTPError as e:
                return LinkStatus(url=url, status="error", error_message=str(e))

    async def check_all_links(self, force: bool = False) -> CheckResult:
        """Check all links in stored posts.

        MAINT-01: Detects and flags dead links in stored posts.
        D-04: Concurrent checks with max 10 simultaneous.

        Args:
            force: If True, recheck all links regardless of cache.

        Returns:
            CheckResult with total_checked, counts, and results list.
        """
        # Get posts with links
        posts = self._repo.get_posts_with_links()

        # Collect all URLs with their post IDs
        url_post_pairs: list[tuple[str, str]] = []  # (x_post_id, url)
        for post in posts:
            # Skip if already checked recently (unless force)
            if not force and not self._should_check(post):
                continue

            # link_urls may already be parsed (from PostsRepository._row_to_dict)
            # or may be a JSON string
            link_urls_raw = post.get("link_urls", [])
            if isinstance(link_urls_raw, str):
                link_urls = json.loads(link_urls_raw)
            else:
                link_urls = link_urls_raw
            for url in link_urls:
                url_post_pairs.append((post["x_post_id"], url))

        if not url_post_pairs:
            return CheckResult(0, 0, 0, 0, [])

        # Check URLs concurrently
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        completed = 0

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            # Create tasks with URL information for proper result matching
            async def check_with_url(post_id: str, url: str) -> tuple[str, str, LinkStatus]:
                result = await self._check_single(client, url, semaphore)
                return (post_id, url, result)

            tasks = []
            for post_id, url in url_post_pairs:
                tasks.append(check_with_url(post_id, url))

            results: list[tuple[str, str, LinkStatus]] = []
            for coro in asyncio.as_completed(tasks):
                post_id, url, result = await coro
                results.append((post_id, url, result))
                completed += 1
                if self._on_progress:
                    self._on_progress(completed, len(url_post_pairs))

        # Aggregate results
        ok_count = sum(1 for _, _, r in results if r.status == "ok")
        dead_count = sum(1 for _, _, r in results if r.status == "dead")
        error_count = sum(1 for _, _, r in results if r.status == "error")

        # Store results per post (aggregate status per post)
        self._store_results(results)

        return CheckResult(
            total_checked=len(results),
            ok_count=ok_count,
            dead_count=dead_count,
            error_count=error_count,
            results=results,
        )

    def _store_results(
        self,
        results: list[tuple[str, str, LinkStatus]],
    ) -> None:
        """Store link status for each post.

        Args:
            results: List of (x_post_id, url, LinkStatus) tuples.
        """
        # Group results by post_id
        post_status: dict[str, list[LinkStatus]] = {}
        for post_id, _, result in results:
            if post_id not in post_status:
                post_status[post_id] = []
            post_status[post_id].append(result)

        # Update each post's link_status
        for post_id, statuses in post_status.items():
            # If any link is dead/error, mark as such
            if any(s.status == "dead" for s in statuses):
                status = "dead"
            elif any(s.status == "error" for s in statuses):
                status = "error"
            else:
                status = "ok"
            self._repo.update_link_status(post_id, status)

    def check_all_links_sync(self, force: bool = False) -> CheckResult:
        """Synchronous wrapper for check_all_links.

        Args:
            force: If True, recheck all links regardless of cache.

        Returns:
            CheckResult with total_checked, counts, and results list.
        """
        return asyncio.run(self.check_all_links(force))