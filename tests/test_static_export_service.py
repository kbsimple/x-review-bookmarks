"""Tests for StaticExportService.

EXPORT-01: xbm export-static generates JSON files for posts, tags, topics, review state.
EXPORT-02: Static web app displays posts with client-side search.
EXPORT-03: Export includes pre-built search index for instant client-side search.
EXPORT-04: User can deploy exported files to Netlify (netlify.toml verified here).

Test classes:
    TestStaticExportService -- core service (Wave 1 fills: JSON files)
    TestSearchIndex         -- search-index.json structure (Wave 1 fills)
    TestIndexHtml           -- index.html content assertions (Wave 3 fills)
    TestNetlifyToml         -- netlify.toml content assertions (Wave 3 fills)
"""

import json
import pytest
from pathlib import Path


class TestStaticExportService:
    """Tests for StaticExportService JSON file generation.

    EXPORT-01: JSON files created for posts, tags, topics, review_state.
    """

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_export_creates_output_directory(self, temp_db_v6, tmp_path):
        """output_dir is created by export() if it does not exist."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_posts_json_contains_all_posts(self, temp_db_v6, tmp_path):
        """posts.json posts array has 3 entries (all seeded posts)."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_posts_json_schema_has_required_fields(self, temp_db_v6, tmp_path):
        """posts.json top-level has version, exported_at, source, post_count, posts."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_posts_json_post_has_tags_field(self, temp_db_v6, tmp_path):
        """Each post in posts.json has a tags field (list of str)."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_posts_json_post_has_topics_field(self, temp_db_v6, tmp_path):
        """Each post in posts.json has a topics field (list of {id, name} dicts)."""
        pass

    def test_posts_json_retweet_has_embedded_post(self, temp_db_v6, tmp_path):
        """Retweet post in posts.json has non-null embedded_post field."""
        from src.repositories.posts import PostsRepository
        repo = PostsRepository(temp_db_v6)
        posts = repo.get_all_with_embedded()
        retweet = next(p for p in posts if p['post_type'] == 'retweet')
        assert retweet['embedded_post'] is not None
        assert retweet['embedded_post']['x_post_id'] == 'emb_001'

    def test_posts_json_original_has_null_embedded_post(self, temp_db_v6, tmp_path):
        """Original post in posts.json has embedded_post: null."""
        from src.repositories.posts import PostsRepository
        repo = PostsRepository(temp_db_v6)
        posts = repo.get_all_with_embedded()
        original = next(p for p in posts if p['post_type'] == 'original')
        assert original['embedded_post'] is None

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_tags_json_has_post_ids(self, temp_db_v6, tmp_path):
        """Each tag in tags.json has a post_ids list."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_topics_json_has_post_ids(self, temp_db_v6, tmp_path):
        """Each topic in topics.json has a post_ids list."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_review_state_json_contains_states(self, temp_db_v6, tmp_path):
        """review_state.json review_states list has 2 entries (seeded states)."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_overwrite_on_rerun(self, temp_db_v6, tmp_path):
        """Second call to export() succeeds and updates files silently."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_empty_database_exports_zero_posts(self, temp_db_v6, tmp_path):
        """Export on empty DB writes posts.json with post_count=0 and no error raised."""
        pass


class TestSearchIndex:
    """Tests for search-index.json structure.

    EXPORT-03: Pre-built search index with denormalized fields.
    """

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_search_index_has_denormalized_tags(self, temp_db_v6, tmp_path):
        """Entry for post_001 has tags='python ml' (space-joined string)."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_search_index_has_denormalized_topics(self, temp_db_v6, tmp_path):
        """Entry for post_001 has topics='Programming Machine Learning' (space-joined)."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_search_index_has_created_at_ts(self, temp_db_v6, tmp_path):
        """Every entry has created_at_ts as an integer (Unix timestamp)."""
        pass

    @pytest.mark.skip(reason="Wave 1: implement StaticExportService first")
    def test_search_index_entry_count_matches_posts(self, temp_db_v6, tmp_path):
        """search-index.json entries count equals posts count (3)."""
        pass


class TestIndexHtml:
    """Tests for index.html content.

    EXPORT-02: Static web app displays posts with client-side search.
    """

    @pytest.mark.skip(reason="Wave 3: implement _write_index_html() first")
    def test_index_html_file_exists(self, temp_db_v6, tmp_path):
        """index.html exists in output directory after export()."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_index_html() first")
    def test_index_html_contains_fetch_calls(self, temp_db_v6, tmp_path):
        """index.html content contains fetch('search-index.json') call."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_index_html() first")
    def test_index_html_contains_date_filter_logic(self, temp_db_v6, tmp_path):
        """index.html content contains 'this_week' date filter case."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_index_html() first")
    def test_index_html_contains_dark_theme_colors(self, temp_db_v6, tmp_path):
        """index.html contains #0f172a (dominant background) in inline CSS."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_index_html() first")
    def test_index_html_contains_view_on_x_copy(self, temp_db_v6, tmp_path):
        """index.html contains 'View on X' string (per UI-SPEC copywriting contract)."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_index_html() first")
    def test_index_html_contains_esc_helper(self, temp_db_v6, tmp_path):
        """index.html contains esc() HTML escaping helper function."""
        pass


class TestNetlifyToml:
    """Tests for netlify.toml content.

    EXPORT-04: netlify.toml present with cache headers for JSON files.
    """

    @pytest.mark.skip(reason="Wave 3: implement _write_netlify_toml() first")
    def test_netlify_toml_exists(self, temp_db_v6, tmp_path):
        """netlify.toml exists in output directory after export()."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_netlify_toml() first")
    def test_netlify_toml_has_cache_headers(self, temp_db_v6, tmp_path):
        """netlify.toml contains Cache-Control header definition."""
        pass

    @pytest.mark.skip(reason="Wave 3: implement _write_netlify_toml() first")
    def test_netlify_toml_has_build_section(self, temp_db_v6, tmp_path):
        """netlify.toml contains [build] section with publish = '.'."""
        pass


# ============================================================================
# Module-level repository tests (Wave 1)
# ============================================================================


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
    # post_001 has FSRS state 2 (review)
    post_001_state = next(s for s in states if s['post_id'] == 'post_001')
    assert post_001_state['state'] == 2
    assert post_001_state['stability'] == pytest.approx(12.5)
    # Internal fields not present
    assert 'user_preference' not in post_001_state
    assert 'fsrs_data' not in post_001_state
