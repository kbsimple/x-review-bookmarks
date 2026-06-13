"""Tests for StaticExportService.

EXPORT-01: xbm export-static generates JSON files for posts, tags, topics, review state.
EXPORT-02: Static web app displays posts with client-side search.
EXPORT-03: Export includes pre-built search index for instant client-side search.
EXPORT-04: User can deploy exported files to Netlify (netlify.toml verified here).

Test classes:
    TestStaticExportService -- core service (Wave 2: JSON files)
    TestSearchIndex         -- search-index.json structure (Wave 2)
    TestIndexHtml           -- index.html content assertions (Wave 3 fills)
    TestNetlifyToml         -- netlify.toml content assertions (Wave 3 fills)
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.services.static_export import StaticExportService


class TestStaticExportService:
    """Tests for StaticExportService JSON file generation.

    EXPORT-01: JSON files created for posts, tags, topics, review_state.
    """

    def test_export_creates_output_directory(self, temp_db_v6, tmp_path):
        """output_dir is created by export() if it does not exist."""
        svc = StaticExportService(temp_db_v6)
        out = tmp_path / "export"
        svc.export(out)
        assert out.exists()
        assert out.is_dir()

    def test_posts_json_contains_all_posts(self, temp_db_v6, tmp_path):
        """posts.json posts array has 3 entries (all seeded posts)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "posts.json").read_text())
        assert data["post_count"] == 3
        assert len(data["posts"]) == 3

    def test_posts_json_schema_has_required_fields(self, temp_db_v6, tmp_path):
        """posts.json top-level has version, exported_at, source, post_count, posts."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "posts.json").read_text())
        assert data["version"] == "1.0"
        assert "exported_at" in data
        assert data["source"] == "xbm-static"
        assert "post_count" in data
        assert "posts" in data

    def test_posts_json_post_has_tags_field(self, temp_db_v6, tmp_path):
        """Each post in posts.json has a tags field (list of str)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "posts.json").read_text())
        post_001 = next(p for p in data["posts"] if p["x_post_id"] == "post_001")
        assert isinstance(post_001["tags"], list)
        assert "python" in post_001["tags"]
        assert "ml" in post_001["tags"]

    def test_posts_json_post_has_topics_field(self, temp_db_v6, tmp_path):
        """Each post in posts.json has a topics field (list of {id, name} dicts)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "posts.json").read_text())
        post_001 = next(p for p in data["posts"] if p["x_post_id"] == "post_001")
        assert isinstance(post_001["topics"], list)
        topic_names = [t["name"] for t in post_001["topics"]]
        assert "Programming" in topic_names

    def test_posts_json_retweet_has_embedded_post(self, temp_db_v6, tmp_path):
        """Retweet post in posts.json has non-null embedded_post field."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "posts.json").read_text())
        retweet = next(p for p in data["posts"] if p["post_type"] == "retweet")
        assert retweet["embedded_post"] is not None
        assert retweet["embedded_post"]["x_post_id"] == "emb_001"

    def test_posts_json_original_has_null_embedded_post(self, temp_db_v6, tmp_path):
        """Original post in posts.json has embedded_post: null."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "posts.json").read_text())
        original = next(p for p in data["posts"] if p["post_type"] == "original")
        assert original["embedded_post"] is None

    def test_tags_json_has_post_ids(self, temp_db_v6, tmp_path):
        """Each tag in tags.json has a post_ids list."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "tags.json").read_text())
        python_tag = next(t for t in data["tags"] if t["name"] == "python")
        assert "post_ids" in python_tag
        assert "post_001" in python_tag["post_ids"]

    def test_topics_json_has_post_ids(self, temp_db_v6, tmp_path):
        """Each topic in topics.json has a post_ids list."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "topics.json").read_text())
        prog = next(t for t in data["topics"] if t["name"] == "Programming")
        assert "post_ids" in prog
        assert "post_001" in prog["post_ids"]

    def test_review_state_json_contains_states(self, temp_db_v6, tmp_path):
        """review_state.json review_states list has 2 entries (seeded states)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "review_state.json").read_text())
        assert len(data["review_states"]) == 2
        post_ids = [s["post_id"] for s in data["review_states"]]
        assert "post_001" in post_ids

    def test_overwrite_on_rerun(self, temp_db_v6, tmp_path):
        """Second call to export() succeeds and updates files silently."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        result = svc.export(tmp_path)
        assert result.post_count == 3

    def test_empty_database_exports_zero_posts(self, temp_db_v6, tmp_path):
        """Export on empty DB writes posts.json with post_count=0 and no error raised."""
        temp_db_v6.execute("DELETE FROM post_tags")
        temp_db_v6.execute("DELETE FROM post_topics")
        temp_db_v6.execute("DELETE FROM post_review_state")
        temp_db_v6.execute("DELETE FROM embedded_posts")
        temp_db_v6.execute("DELETE FROM posts")
        temp_db_v6.commit()
        svc = StaticExportService(temp_db_v6)
        result = svc.export(tmp_path)
        assert result.post_count == 0
        data = json.loads((tmp_path / "posts.json").read_text())
        assert data["post_count"] == 0
        assert data["posts"] == []


class TestSearchIndex:
    """Tests for search-index.json structure.

    EXPORT-03: Pre-built search index with denormalized fields.
    """

    def test_search_index_has_denormalized_tags(self, temp_db_v6, tmp_path):
        """Entry for post_001 has tags='ml python' (space-joined string, sorted)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "search-index.json").read_text())
        entry = next(e for e in data["entries"] if e["id"] == "post_001")
        assert "ml" in entry["tags"]
        assert "python" in entry["tags"]
        assert isinstance(entry["tags"], str)

    def test_search_index_has_denormalized_topics(self, temp_db_v6, tmp_path):
        """Entry for post_001 has topics string with both topic names."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "search-index.json").read_text())
        entry = next(e for e in data["entries"] if e["id"] == "post_001")
        assert "Programming" in entry["topics"]
        assert "Machine Learning" in entry["topics"]
        assert isinstance(entry["topics"], str)

    def test_search_index_has_created_at_ts(self, temp_db_v6, tmp_path):
        """Every entry has created_at_ts as an integer (Unix timestamp)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        data = json.loads((tmp_path / "search-index.json").read_text())
        for entry in data["entries"]:
            assert isinstance(entry["created_at_ts"], int)
            assert entry["created_at_ts"] > 0

    def test_search_index_entry_count_matches_posts(self, temp_db_v6, tmp_path):
        """search-index.json entries count equals posts count (3)."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        posts_data = json.loads((tmp_path / "posts.json").read_text())
        index_data = json.loads((tmp_path / "search-index.json").read_text())
        assert len(index_data["entries"]) == posts_data["post_count"]


class TestIndexHtml:
    """Tests for index.html content. EXPORT-02."""

    def test_index_html_file_exists(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        assert (tmp_path / "index.html").exists()

    def test_index_html_contains_fetch_calls(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "fetch('search-index.json')" in html

    def test_index_html_contains_date_filter_logic(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "this_week" in html

    def test_index_html_contains_dark_theme_colors(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "#0f172a" in html

    def test_index_html_contains_view_on_x_copy(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "View on X" in html

    def test_index_html_contains_esc_helper(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "function esc(" in html

    def test_index_html_contains_linkify_helper(self, temp_db_v6, tmp_path):
        """index.html contains linkify() for converting URLs in text to links."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "function linkify(" in html

    def test_index_html_contains_profile_link_helper(self, temp_db_v6, tmp_path):
        """index.html contains profileLink() for linking @usernames to x.com profiles."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "function profileLink(" in html
        assert "https://x.com/" in html


class TestIndexHtmlCarousel:
    """Tests for carousel mode additions to index.html. VIEWER-01 through VIEWER-05."""

    def test_mode_switcher_button_class_present(self, temp_db_v6, tmp_path):
        """VIEWER-01: mode switcher button class present in generated HTML."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "mode-btn" in html

    def test_localstorage_key_present(self, temp_db_v6, tmp_path):
        """VIEWER-02: localStorage key xbm_mode present in generated HTML."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "xbm_mode" in html

    def test_carousel_render_function_present(self, temp_db_v6, tmp_path):
        """VIEWER-03: renderCarousel function and carouselIndex variable present."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "renderCarousel" in html
        assert "carouselIndex" in html

    def test_keyboard_nav_listener_present(self, temp_db_v6, tmp_path):
        """VIEWER-04: keyboard nav listener with ArrowRight/ArrowLeft/Escape present."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "ArrowRight" in html
        assert "ArrowLeft" in html
        assert "Escape" in html

    def test_carousel_nav_dom_ids_present(self, temp_db_v6, tmp_path):
        """VIEWER-04/05: carousel-nav, carousel-prev, carousel-next, carousel-counter present."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "carousel-nav" in html
        assert "carousel-prev" in html
        assert "carousel-next" in html
        assert "carousel-counter" in html

    def test_oembed_reinit_called_in_carousel(self, temp_db_v6, tmp_path):
        """VIEWER-05: twttr.widgets.load present for oEmbed re-init in carousel."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "twttr.widgets.load" in html


class TestNetlifyToml:
    """Tests for netlify.toml content. EXPORT-04."""

    def test_netlify_toml_exists(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        assert (tmp_path / "netlify.toml").exists()

    def test_netlify_toml_has_cache_headers(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        content = (tmp_path / "netlify.toml").read_text()
        assert "Cache-Control" in content

    def test_netlify_toml_has_build_section(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        content = (tmp_path / "netlify.toml").read_text()
        assert "[build]" in content
        assert 'publish = "."' in content


def test_get_all_with_embedded_returns_all_posts(temp_db_v6):
    """PostsRepository.get_all_with_embedded() returns all posts with embedded data."""
    from src.repositories.posts import PostsRepository
    repo = PostsRepository(temp_db_v6)
    posts = repo.get_all_with_embedded()
    assert len(posts) == 3
    # Ordered newest first
    assert posts[0]['x_post_id'] == 'post_003'
    # All have embedded_post key
    assert all('embedded_post' in p for p in posts)
    # Retweet has embedded post
    retweet = next(p for p in posts if p['post_type'] == 'retweet')
    assert retweet['embedded_post'] is not None
    assert isinstance(retweet['embedded_post']['media_urls'], list)


def test_get_all_review_states_returns_seeded_states(temp_db_v6):
    """ReviewStateRepository.get_all() returns all seeded review states."""
    from src.repositories.review_state import ReviewStateRepository
    repo = ReviewStateRepository(temp_db_v6)
    states = repo.get_all()
    assert len(states) == 2
    post_ids = [s['post_id'] for s in states]
    assert 'post_001' in post_ids
    assert 'post_002' in post_ids
    post_001_state = next(s for s in states if s['post_id'] == 'post_001')
    assert post_001_state['state'] == 2
    assert post_001_state['stability'] == pytest.approx(12.5)
    assert 'user_preference' not in post_001_state
    assert 'fsrs_data' not in post_001_state


class TestRichEmbeds:
    """Tests for StaticExportService rich_embeds path (OEMBED-01, OEMBED-02, OEMBED-04)."""

    def test_rich_embeds_adds_oembed_html_to_posts_json(self, temp_db_v6, tmp_path):
        """With rich_embeds=True and mocked OEmbedService, oembed_html appears in posts.json."""
        fake_html = "<blockquote class='twitter-tweet'>...</blockquote>"
        mock_svc_instance = MagicMock()
        mock_svc_instance.fetch_all.return_value = {
            "post_001": fake_html,
            "post_002": None,   # deleted/protected
            "post_003": fake_html,
        }
        with patch("src.services.oembed.OEmbedService", return_value=mock_svc_instance):
            svc = StaticExportService(temp_db_v6)
            svc.export(tmp_path, rich_embeds=True)
        data = json.loads((tmp_path / "posts.json").read_text())
        post_001 = next(p for p in data["posts"] if p["x_post_id"] == "post_001")
        post_002 = next(p for p in data["posts"] if p["x_post_id"] == "post_002")
        assert post_001["oembed_html"] == fake_html
        assert post_002["oembed_html"] is None

    def test_no_rich_embeds_omits_oembed_html_field(self, temp_db_v6, tmp_path):
        """With rich_embeds=False (default), posts.json posts do not have oembed_html key."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)  # default: rich_embeds=False
        data = json.loads((tmp_path / "posts.json").read_text())
        for post in data["posts"]:
            assert "oembed_html" not in post

    def test_rich_embeds_calls_fetch_all_with_all_post_ids(self, temp_db_v6, tmp_path):
        """OEmbedService.fetch_all is called with (post_id, username) pairs for all 3 posts."""
        mock_svc_instance = MagicMock()
        mock_svc_instance.fetch_all.return_value = {
            "post_001": None,
            "post_002": None,
            "post_003": None,
        }
        with patch("src.services.oembed.OEmbedService", return_value=mock_svc_instance):
            svc = StaticExportService(temp_db_v6)
            svc.export(tmp_path, rich_embeds=True)
        called_pairs = mock_svc_instance.fetch_all.call_args[0][0]
        called_ids = {pair[0] for pair in called_pairs}
        assert called_ids == {"post_001", "post_002", "post_003"}
