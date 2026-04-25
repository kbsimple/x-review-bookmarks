"""Tests for tags repository.

Tests for:
- Get or create tag
- Assign tag to post
- Remove tag from post
- Get post tags
- Get posts by tag

ORG-01: User can assign tags to bookmarked posts.
"""

import pytest


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_get_or_create_tag():
    """Verify get_or_create_tag returns existing tag ID or creates new one.

    ORG-01: User can assign tags to bookmarked posts.
    """
    pass


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_get_or_create_tag_case_insensitive():
    """Verify tag names are normalized to lowercase.

    ORG-01: Tag names should be case-insensitive.
    """
    pass


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_assign_tag_to_post():
    """Verify a tag can be assigned to a post.

    ORG-01: User can assign tags to bookmarked posts.
    """
    pass


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_assign_tag_to_post_idempotent():
    """Verify assigning same tag twice is idempotent.

    ORG-01: Re-assigning same tag should not cause error.
    """
    pass


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_remove_tag_from_post():
    """Verify a tag can be removed from a post.

    ORG-01: User can remove tags from bookmarked posts.
    """
    pass


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_get_post_tags():
    """Verify all tags for a post can be retrieved.

    ORG-01: User can view tags assigned to a post.
    """
    pass


@pytest.mark.skip(reason="Implementation pending in plan 04-01")
def test_get_posts_by_tag():
    """Verify all posts with a specific tag can be retrieved.

    ORG-01: User can filter posts by tag.
    """
    pass