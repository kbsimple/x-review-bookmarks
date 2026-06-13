"""Tests for OEmbedService (Phase 15, OEMBED-01, OEMBED-02)."""

from unittest.mock import patch, MagicMock

from src.services.oembed import OEmbedService


class TestOEmbedService:
    """Unit tests for OEmbedService.fetch_oembed and fetch_all."""

    def test_fetch_oembed_success_returns_html(self):
        """200 response with html field returns the HTML string."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html": "<blockquote>...</blockquote>"}
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            svc = OEmbedService()
            result = svc.fetch_oembed("1234567890")
        assert result == "<blockquote>...</blockquote>"
        mock_get.assert_called_once()

    def test_fetch_oembed_404_returns_none(self):
        """404 response returns None (deleted/protected post)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.get", return_value=mock_resp):
            svc = OEmbedService()
            result = svc.fetch_oembed("9999999999")
        assert result is None

    def test_fetch_oembed_network_error_returns_none(self):
        """Network exception (e.g. connection timeout) returns None."""
        with patch("httpx.get", side_effect=Exception("Connection timeout")):
            svc = OEmbedService()
            result = svc.fetch_oembed("1234567890")
        assert result is None

    def test_fetch_all_maps_ids_to_html(self):
        """fetch_all returns dict mapping post_id -> html or None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html": "<blockquote>test</blockquote>"}
        with patch("httpx.get", return_value=mock_resp):
            svc = OEmbedService(request_delay=0)  # no sleep in tests
            result = svc.fetch_all(["id1", "id2"])
        assert result == {
            "id1": "<blockquote>test</blockquote>",
            "id2": "<blockquote>test</blockquote>",
        }

    def test_fetch_all_invokes_progress_callback(self):
        """on_progress callback is called once per post with (completed, total)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html": "<blockquote></blockquote>"}
        calls = []
        with patch("httpx.get", return_value=mock_resp):
            svc = OEmbedService(request_delay=0)
            svc.fetch_all(["a", "b", "c"], on_progress=lambda c, t: calls.append((c, t)))
        assert calls == [(1, 3), (2, 3), (3, 3)]
