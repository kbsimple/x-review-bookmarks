"""OEmbedService -- fetches Twitter/X oEmbed HTML for posts.

Calls the public oEmbed endpoint (no auth required) and returns
pre-rendered blockquote HTML for storage in posts.json.

Usage:
    svc = OEmbedService()
    html_map = svc.fetch_all(["1234567890", "9876543210"])
    # {"1234567890": "<blockquote ...>", "9876543210": None}
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import httpx


_OEMBED_API = "https://publish.twitter.com/oembed"
_POST_URL = "https://x.com/i/web/status/{post_id}"
_DEFAULT_DELAY = 0.15


class OEmbedService:
    """Fetches oEmbed blockquote HTML for X posts.

    Uses omit_script=true so the returned HTML is a bare <blockquote>
    without the widget.js <script> tag — callers handle loading the script.

    Args:
        request_delay: Seconds to sleep between successive API calls.
    """

    def __init__(self, request_delay: float = _DEFAULT_DELAY) -> None:
        self._delay = request_delay

    def fetch_oembed(self, post_id: str) -> Optional[str]:
        """Return oEmbed HTML for one post, or None if unavailable.

        Returns None for deleted/protected posts (404) and any network error.
        """
        url = _POST_URL.format(post_id=post_id)
        try:
            resp = httpx.get(
                _OEMBED_API,
                params={"url": url, "omit_script": "true", "dnt": "true"},
                timeout=10.0,
                follow_redirects=True,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json().get("html")
        except Exception:
            return None

    def fetch_all(
        self,
        post_ids: list[str],
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> dict[str, Optional[str]]:
        """Fetch oEmbed HTML for a list of post IDs.

        Args:
            post_ids: X post IDs to fetch.
            on_progress: Optional callback invoked as (completed, total) after each fetch.

        Returns:
            Dict mapping post_id -> HTML string, or None for unavailable posts.
        """
        results: dict[str, Optional[str]] = {}
        total = len(post_ids)
        for i, post_id in enumerate(post_ids):
            results[post_id] = self.fetch_oembed(post_id)
            if on_progress:
                on_progress(i + 1, total)
            if i < total - 1:
                time.sleep(self._delay)
        return results
