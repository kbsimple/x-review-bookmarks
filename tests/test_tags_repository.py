"""Tests for TagsRepository.

ORG-01: User can assign tags to bookmarked posts.
"""

import pytest
from src.repositories.tags import TagsRepository
from src.db.schema import SCHEMA_V1, SCHEMA_V2, SCHEMA_V4_MIGRATION


@pytest.fixture
def db_with_tags(temp_db):
    """Create database with tags tables."""
    temp_db.executescript(SCHEMA_V1)
    temp_db.executescript(SCHEMA_V2)
    temp_db.executescript(SCHEMA_V4_MIGRATION)

    # Add a test post
    temp_db.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Test post', 'user123', 'testuser')""",
        ('post_123',)
    )
    temp_db.commit()
    return temp_db


def test_get_or_create_tag_new(db_with_tags):
    """Creating a new tag returns the new ID."""
    repo = TagsRepository(db_with_tags)
    tag_id = repo.get_or_create_tag("python")
    assert tag_id == 1

    # Verify tag was created
    tag = repo.get_tag_by_name("python")
    assert tag is not None
    assert tag['name'] == "python"


def test_get_or_create_tag_existing(db_with_tags):
    """Creating duplicate tag returns existing ID."""
    repo = TagsRepository(db_with_tags)
    id1 = repo.get_or_create_tag("python")
    id2 = repo.get_or_create_tag("python")
    assert id1 == id2


def test_get_or_create_tag_normalizes(db_with_tags):
    """Tag names are normalized to lowercase."""
    repo = TagsRepository(db_with_tags)
    id1 = repo.get_or_create_tag("Python")
    id2 = repo.get_or_create_tag("PYTHON")
    assert id1 == id2

    tag = repo.get_tag_by_name("python")
    assert tag['name'] == "python"


def test_assign_tag(db_with_tags):
    """Assigning tag to post creates link."""
    repo = TagsRepository(db_with_tags)
    tag_id = repo.get_or_create_tag("python")
    repo.assign_tag("post_123", tag_id)

    tags = repo.get_post_tags("post_123")
    assert len(tags) == 1
    assert tags[0]['name'] == "python"


def test_assign_tag_idempotent(db_with_tags):
    """Assigning same tag twice is idempotent."""
    repo = TagsRepository(db_with_tags)
    tag_id = repo.get_or_create_tag("python")
    repo.assign_tag("post_123", tag_id)
    repo.assign_tag("post_123", tag_id)

    tags = repo.get_post_tags("post_123")
    assert len(tags) == 1


def test_remove_tag(db_with_tags):
    """Removing tag from post deletes link."""
    repo = TagsRepository(db_with_tags)
    tag_id = repo.get_or_create_tag("python")
    repo.assign_tag("post_123", tag_id)

    repo.remove_tag("post_123", tag_id)
    tags = repo.get_post_tags("post_123")
    assert len(tags) == 0


def test_get_post_tags(db_with_tags):
    """Getting tags for post returns all tags."""
    repo = TagsRepository(db_with_tags)
    tag1 = repo.get_or_create_tag("python")
    tag2 = repo.get_or_create_tag("ml")
    repo.assign_tag("post_123", tag1)
    repo.assign_tag("post_123", tag2)

    tags = repo.get_post_tags("post_123")
    assert len(tags) == 2
    names = [t['name'] for t in tags]
    assert "ml" in names  # alphabetical order
    assert "python" in names


def test_get_posts_by_tag(db_with_tags):
    """Getting posts by tag returns all matching posts."""
    repo = TagsRepository(db_with_tags)
    tag_id = repo.get_or_create_tag("python")
    repo.assign_tag("post_123", tag_id)

    posts = repo.get_posts_by_tag(tag_id)
    assert "post_123" in posts


def test_list_tags(db_with_tags):
    """Listing tags returns all tags alphabetically."""
    repo = TagsRepository(db_with_tags)
    repo.get_or_create_tag("python")
    repo.get_or_create_tag("ml")
    repo.get_or_create_tag("career")

    tags = repo.list_tags()
    assert len(tags) == 3
    names = [t['name'] for t in tags]
    assert names == ["career", "ml", "python"]  # alphabetical


def test_delete_tag(db_with_tags):
    """Deleting tag cascade removes post_tags entries."""
    repo = TagsRepository(db_with_tags)
    tag_id = repo.get_or_create_tag("python")
    repo.assign_tag("post_123", tag_id)

    repo.delete_tag(tag_id)

    # Tag no longer exists
    assert repo.get_tag_by_name("python") is None
    # Post_tags entry cascade deleted
    tags = repo.get_post_tags("post_123")
    assert len(tags) == 0


def test_get_tag_by_name_not_found(db_with_tags):
    """get_tag_by_name returns None for non-existent tag."""
    repo = TagsRepository(db_with_tags)

    result = repo.get_tag_by_name("nonexistent")
    assert result is None


def test_get_tag_by_name_normalized(db_with_tags):
    """get_tag_by_name normalizes the search term."""
    repo = TagsRepository(db_with_tags)
    repo.get_or_create_tag("Python")

    # Search with different case
    tag = repo.get_tag_by_name("PYTHON")
    assert tag is not None
    assert tag['name'] == "python"