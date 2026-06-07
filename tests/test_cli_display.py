"""Tests for CLI display functions for embedded posts.

Tests CLI-06, CLI-07, CLI-08: Display of quote tweets, retweets,
unavailable posts, and media URLs in terminal output.

This test module follows TDD RED phase: tests define expected behavior
before implementation exists. All tests should FAIL initially.
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.display import display_post


# ============================================================================
# Task 1: Test Fixtures Exist and Are Importable
# ============================================================================


class TestFixtures:
    """Tests for test fixture availability and structure."""

    def test_quote_tweet_post_fixture(self, quote_tweet_post):
        """Verify quote_tweet_post fixture has expected structure.

        Expected behavior:
        - post_type is 'quote'
        - Has author info for quoter
        - Has text for user's commentary
        - embedded_post dict contains quoted content
        """
        assert quote_tweet_post["post_type"] == "quote"
        assert "author_username" in quote_tweet_post
        assert "text" in quote_tweet_post
        assert "embedded_post" in quote_tweet_post
        assert quote_tweet_post["embedded_post"]["available"] is True

    def test_retweet_post_fixture(self, retweet_post):
        """Verify retweet_post fixture has expected structure.

        Expected behavior:
        - post_type is 'retweet'
        - Has author info for retweeter
        - embedded_post dict contains original content
        """
        assert retweet_post["post_type"] == "retweet"
        assert "author_username" in retweet_post
        assert "embedded_post" in retweet_post
        assert retweet_post["embedded_post"]["available"] is True

    def test_unavailable_post_fixture(self, unavailable_post):
        """Verify unavailable_post fixture has expected structure.

        Expected behavior:
        - post_type is 'retweet' or 'quote'
        - embedded_post has available=False
        - Author info present (partial)
        """
        assert unavailable_post["post_type"] in ("retweet", "quote")
        assert "embedded_post" in unavailable_post
        assert unavailable_post["embedded_post"]["available"] is False
        assert "author_username" in unavailable_post["embedded_post"]

    def test_original_post_with_media_fixture(self, original_post_with_media):
        """Verify original_post_with_media fixture has expected structure.

        Expected behavior:
        - post_type is 'original'
        - Has media_urls list with 2-3 URLs
        - No embedded_post key
        """
        assert original_post_with_media["post_type"] == "original"
        assert "media_urls" in original_post_with_media
        assert len(original_post_with_media["media_urls"]) >= 2
        assert "embedded_post" not in original_post_with_media


# ============================================================================
# Task 2: Quote Tweet Rendering Tests (CLI-06)
# ============================================================================


class TestQuoteTweetRendering:
    """Tests for quote tweet display per CLI-06 and D-01, D-02, D-08."""

    def test_quote_tweet_nested_panel(self, quote_tweet_post):
        """Verify quote tweet produces nested Panel structure.

        Per D-01: Outer Panel for quoter, inner content for quoted.

        Expected behavior:
        - Output contains both quoter's author and quoted author
        - Nested structure visible (outer panel, inner content)
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, quote_tweet_post)

        output = console.file.getvalue()

        # Should show quoter's username
        assert "@quoter_user" in output

        # Should show quoted author's username
        assert "@quoted_user" in output

        # Should show quoter's commentary text
        assert "This is my commentary" in output

        # Should show quoted content
        assert "This is the original quoted content" in output

    def test_quote_tweet_attribution(self, quote_tweet_post):
        """Verify quote attribution appears above quoted content.

        Per D-02: "[dim]Quoting @username[/dim]" above inner Panel.

        Expected behavior:
        - Attribution line present
        - Shows quoted author's username
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, quote_tweet_post)

        output = console.file.getvalue()

        # Should show attribution line for quoted author
        assert "Quoting @quoted_user" in output

    def test_quote_tweet_visual_hierarchy(self, quote_tweet_post):
        """Verify quoter's text is prominent, quoted content dimmed.

        Per D-01: Visual hierarchy with quoted content subdued.

        Expected behavior:
        - Quoter's text appears before quoted text
        - Quoted content has dim border styling
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, quote_tweet_post)

        output = console.file.getvalue()

        # Quoter's commentary should appear in the output
        assert "This is my commentary on the quoted post" in output

        # Quoted content should also be present
        assert "This is the original quoted content" in output

        # Quoter's username should be prominent (cyan/bold styling in Rich)
        # The exact format depends on implementation, but quoter should appear
        assert "@quoter_user" in output

    def test_quote_tweet_combined_media_urls(self, quote_tweet_post):
        """Verify media URLs from both quoter and quoted are displayed.

        Per D-08: All media URLs shown together, no separate sections.

        Expected behavior:
        - All media URLs from quoter displayed
        - All media URLs from quoted displayed
        - No separate "Quoted media" section
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, quote_tweet_post)

        output = console.file.getvalue()

        # Should show quoter's media URL
        assert "quoter_image.jpg" in output

        # Should show quoted content's media URLs
        assert "quoted_image1.jpg" in output
        assert "quoted_image2.jpg" in output


# ============================================================================
# Task 3: Retweet Rendering Tests (CLI-07)
# ============================================================================


class TestRetweetRendering:
    """Tests for retweet display per CLI-07 and D-03, D-04, D-08."""

    def test_retweet_header(self, retweet_post):
        """Verify retweet shows 'Reposted from @username' header.

        Per D-03: Header above content panel with original author attribution.

        Expected behavior:
        - "Reposted from @original_author" appears in output
        - Header appears above content
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, retweet_post)

        output = console.file.getvalue()

        # Should show reposted from header
        assert "Reposted from @original_author" in output

    def test_retweet_reposter_info(self, retweet_post):
        """Verify retweet shows 'Reposted by @retweeter' line.

        Per D-04: Shows who retweeted while keeping original author prominent.

        Expected behavior:
        - "Reposted by @retweeter_user" appears in output
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, retweet_post)

        output = console.file.getvalue()

        # Should show reposter info
        assert "Reposted by @retweeter_user" in output

    def test_retweet_content_panel(self, retweet_post):
        """Verify original content displayed in standard Panel.

        Expected behavior:
        - Original content displayed
        - Original author shown with [bold cyan]@username styling
        - Same styling as original posts
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, retweet_post)

        output = console.file.getvalue()

        # Should show original author prominently
        assert "@original_author" in output

        # Should show original content
        assert "This is the original post content that was retweeted" in output

        # Should show original author's display name
        assert "Original Author" in output

    def test_retweet_media_urls(self, retweet_post):
        """Verify media URLs from embedded post displayed.

        Per D-07: URLs displayed with 🔗 prefix.

        Expected behavior:
        - Embedded media URLs displayed
        - Link URLs also shown
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, retweet_post)

        output = console.file.getvalue()

        # Should show media URL from embedded post
        assert "original_image.jpg" in output

        # Should show link URL from embedded post
        assert "example.com/article" in output


# ============================================================================
# Task 4: Unavailable Post Handling Tests (D-05, D-06)
# ============================================================================


class TestUnavailablePostHandling:
    """Tests for unavailable embedded post handling per D-05, D-06."""

    def test_unavailable_placeholder_panel(self, unavailable_post):
        """Verify unavailable post shows red-bordered placeholder.

        Per D-05: Panel with border_style="red" for unavailable posts.

        Expected behavior:
        - Placeholder content displayed
        - Visual distinction from available content
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, unavailable_post)

        output = console.file.getvalue()

        # Should show unavailable message
        assert "Original post unavailable" in output

    def test_unavailable_message(self, unavailable_post):
        """Verify 'Original post unavailable' message displayed.

        Per D-05: Clear message when embedded post is deleted/protected.

        Expected behavior:
        - Clear unavailable message
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, unavailable_post)

        output = console.file.getvalue()

        # Should show the unavailable message
        assert "Original post unavailable" in output

    def test_unavailable_with_author(self, unavailable_post):
        """Verify author shown when known but post unavailable.

        Per D-06: "[dim]Originally by @username[/dim]" shown.

        Expected behavior:
        - Partial author info displayed
        - Shows who originally posted
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, unavailable_post)

        output = console.file.getvalue()

        # Should show author attribution even though post unavailable
        assert "Originally by @deleted_author" in output


# ============================================================================
# Task 5: Media URL Display Tests (CLI-08)
# ============================================================================


class TestMediaUrlDisplay:
    """Tests for media URL display per CLI-08 and D-07, D-08."""

    def test_media_urls_display(self, original_post_with_media):
        """Verify media URLs displayed with 🔗 prefix and indentation.

        Per D-07: URLs indented, dim styled, with link icon.

        Expected behavior:
        - Each URL displayed
        - 🔗 prefix present
        - Dim styling
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, original_post_with_media)

        output = console.file.getvalue()

        # Should show all media URLs
        assert "photo1.jpg" in output
        assert "photo2.jpg" in output
        assert "photo3.jpg" in output

        # Should show link icon (🔗)
        # Note: In Rich output, this may appear as emoji or text
        # Check for presence of URLs with proper context
        assert "https://example.com/photo1.jpg" in output

    def test_media_urls_quote_combined(self, quote_tweet_post):
        """Verify quote tweet shows combined media URLs from both sources.

        Per D-08: All URLs shown together, no separate sections.

        Expected behavior:
        - Both quoter and quoted media URLs present
        - Single combined display
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, quote_tweet_post)

        output = console.file.getvalue()

        # Quoter's media
        assert "quoter_image.jpg" in output

        # Quoted content's media
        assert "quoted_image1.jpg" in output
        assert "quoted_image2.jpg" in output

    def test_media_urls_retweet(self, retweet_post):
        """Verify retweet shows embedded media URLs correctly.

        Expected behavior:
        - Embedded post media URLs displayed
        - Same format as original post media
        """
        console = Console(file=StringIO(), width=80)
        display_post(console, retweet_post)

        output = console.file.getvalue()

        # Should show embedded media URL
        assert "original_image.jpg" in output

        # Should show link URL
        assert "example.com/article" in output