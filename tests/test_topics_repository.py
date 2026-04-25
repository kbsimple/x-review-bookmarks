"""Tests for TopicsRepository.

ORG-02: User can create and manage a predefined topic taxonomy.
ORG-04: User can review and approve AI-suggested topic assignments.
"""

import pytest
import sqlite3
from src.repositories.topics import TopicsRepository
from src.db.schema import SCHEMA_V1, SCHEMA_V2, SCHEMA_V4_MIGRATION


@pytest.fixture
def db_with_topics(temp_db):
    """Create database with topics tables and a test post."""
    temp_db.executescript(SCHEMA_V1)
    temp_db.executescript(SCHEMA_V2)
    temp_db.executescript(SCHEMA_V4_MIGRATION)

    # Add a test post
    temp_db.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Test post about Python programming', 'user123', 'testuser')""",
        ('post_123',)
    )
    temp_db.commit()
    return temp_db


def test_create_topic(db_with_topics):
    """Creating a topic returns the ID."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming", "Software development content")
    assert topic_id == 1

    topic = repo.get_topic_by_id(topic_id)
    assert topic['name'] == "Programming"
    assert topic['description'] == "Software development content"


def test_create_topic_duplicate_name(db_with_topics):
    """Duplicate topic name raises IntegrityError."""
    repo = TopicsRepository(db_with_topics)
    repo.create_topic("Programming", "Software development")

    with pytest.raises(sqlite3.IntegrityError):
        repo.create_topic("Programming", "Different description")


def test_get_topic_by_id(db_with_topics):
    """Getting topic by ID returns the topic."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")

    topic = repo.get_topic_by_id(topic_id)
    assert topic is not None
    assert topic['name'] == "Programming"


def test_get_topic_by_name(db_with_topics):
    """Getting topic by name returns the topic."""
    repo = TopicsRepository(db_with_topics)
    repo.create_topic("Programming")

    topic = repo.get_topic_by_name("Programming")
    assert topic is not None
    assert topic['name'] == "Programming"


def test_list_topics(db_with_topics):
    """Listing topics returns all topics alphabetically."""
    repo = TopicsRepository(db_with_topics)
    repo.create_topic("Programming")
    repo.create_topic("Machine Learning")
    repo.create_topic("Career")

    topics = repo.list_topics()
    assert len(topics) == 3
    names = [t['name'] for t in topics]
    assert names == ["Career", "Machine Learning", "Programming"]


def test_update_topic(db_with_topics):
    """Updating topic changes the fields."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming", "Old description")

    repo.update_topic(topic_id, name="Software Development", description="New description")

    topic = repo.get_topic_by_id(topic_id)
    assert topic['name'] == "Software Development"
    assert topic['description'] == "New description"


def test_delete_topic(db_with_topics):
    """Deleting topic cascade removes post_topics entries."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.assign_topic_to_post("post_123", topic_id)

    repo.delete_topic(topic_id)

    assert repo.get_topic_by_id(topic_id) is None
    topics = repo.get_post_topics("post_123")
    assert len(topics) == 0


def test_assign_topic_to_post(db_with_topics):
    """Assigning topic to post creates link."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.assign_topic_to_post("post_123", topic_id)

    topics = repo.get_post_topics("post_123")
    assert len(topics) == 1
    assert topics[0]['name'] == "Programming"
    assert topics[0]['source'] == "user"


def test_assign_topic_to_post_with_confidence(db_with_topics):
    """Assigning with confidence stores the score."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.assign_topic_to_post("post_123", topic_id, confidence=0.85, source="ai-approved")

    topics = repo.get_post_topics("post_123")
    assert topics[0]['confidence'] == 0.85
    assert topics[0]['source'] == "ai-approved"


def test_remove_topic_from_post(db_with_topics):
    """Removing topic from post deletes link."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.assign_topic_to_post("post_123", topic_id)

    repo.remove_topic_from_post("post_123", topic_id)

    topics = repo.get_post_topics("post_123")
    assert len(topics) == 0


def test_get_posts_by_topic(db_with_topics):
    """Getting posts by topic returns matching posts."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.assign_topic_to_post("post_123", topic_id)

    posts = repo.get_posts_by_topic(topic_id)
    assert "post_123" in posts


def test_create_pending_assignment(db_with_topics):
    """Creating pending assignment stores it."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")

    pending_id = repo.create_pending_assignment("post_123", topic_id, 0.92)

    pending = repo.get_pending_assignments()
    assert len(pending) == 1
    assert pending[0]['post_id'] == "post_123"
    assert pending[0]['topic_id'] == topic_id
    assert pending[0]['confidence'] == 0.92


def test_approve_pending_assignment(db_with_topics):
    """Approving pending assignment moves to post_topics."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    pending_id = repo.create_pending_assignment("post_123", topic_id, 0.92)

    repo.approve_pending_assignment(pending_id)

    # Pending is removed
    pending = repo.get_pending_assignments()
    assert len(pending) == 0

    # Topic is assigned
    topics = repo.get_post_topics("post_123")
    assert len(topics) == 1
    assert topics[0]['source'] == "ai-approved"
    assert topics[0]['confidence'] == 0.92


def test_reject_pending_assignment(db_with_topics):
    """Rejecting pending assignment deletes without assigning."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    pending_id = repo.create_pending_assignment("post_123", topic_id, 0.92)

    repo.reject_pending_assignment(pending_id)

    # Pending is removed
    pending = repo.get_pending_assignments()
    assert len(pending) == 0

    # Topic is NOT assigned
    topics = repo.get_post_topics("post_123")
    assert len(topics) == 0


def test_get_pending_assignments_with_topic_info(db_with_topics):
    """Getting pending assignments includes topic name."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.create_pending_assignment("post_123", topic_id, 0.92)

    pending = repo.get_pending_assignments()
    assert pending[0]['topic_name'] == "Programming"


def test_clear_pending_assignments(db_with_topics):
    """Clearing pending assignments removes them."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")
    repo.create_pending_assignment("post_123", topic_id, 0.92)

    count = repo.clear_pending_assignments()
    assert count == 1

    pending = repo.get_pending_assignments()
    assert len(pending) == 0


def test_get_pending_assignments_filtered_by_post(db_with_topics):
    """Getting pending assignments can filter by post ID."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")

    # Add another test post
    db_with_topics.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Another test post', 'user456', 'otheruser')""",
        ('post_456',)
    )
    db_with_topics.commit()

    repo.create_pending_assignment("post_123", topic_id, 0.92)
    repo.create_pending_assignment("post_456", topic_id, 0.75)

    # Get all pending
    all_pending = repo.get_pending_assignments()
    assert len(all_pending) == 2

    # Filter by post
    post_123_pending = repo.get_pending_assignments(post_id="post_123")
    assert len(post_123_pending) == 1
    assert post_123_pending[0]['post_id'] == "post_123"


def test_clear_pending_assignments_by_post(db_with_topics):
    """Clearing pending assignments can filter by post ID."""
    repo = TopicsRepository(db_with_topics)
    topic_id = repo.create_topic("Programming")

    # Add another test post
    db_with_topics.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Another test post', 'user456', 'otheruser')""",
        ('post_456',)
    )
    db_with_topics.commit()

    repo.create_pending_assignment("post_123", topic_id, 0.92)
    repo.create_pending_assignment("post_456", topic_id, 0.75)

    # Clear only for post_123
    count = repo.clear_pending_assignments(post_id="post_123")
    assert count == 1

    # post_456 should still have pending
    remaining = repo.get_pending_assignments()
    assert len(remaining) == 1
    assert remaining[0]['post_id'] == "post_456"


def test_list_topics_with_hierarchy(db_with_topics):
    """Listing topics can include child count for hierarchy."""
    repo = TopicsRepository(db_with_topics)

    # Create parent topic
    parent_id = repo.create_topic("Programming", "Software development")

    # Create child topics
    repo.create_topic("Python", "Python programming", parent_id=parent_id)
    repo.create_topic("JavaScript", "JavaScript programming", parent_id=parent_id)

    topics = repo.list_topics(include_hierarchy=True)

    # Find the parent topic
    parent_topic = next(t for t in topics if t['name'] == "Programming")
    assert parent_topic['child_count'] == 2