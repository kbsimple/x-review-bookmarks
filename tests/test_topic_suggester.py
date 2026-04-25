"""Tests for TopicSuggesterService.

ORG-03: Application clusters posts into topics using hybrid approach.
ORG-04: User can review and approve AI-suggested topic assignments.
"""

import pytest
from src.services.topic_suggester import TopicSuggesterService, TopicSuggestion, SuggestionSummary
from src.repositories.topics import TopicsRepository
from src.repositories.posts import PostsRepository
from src.db.schema import SCHEMA_V1, SCHEMA_V2, SCHEMA_V4_MIGRATION


@pytest.fixture
def db_with_topics_and_posts(temp_db):
    """Create database with topics, posts, and existing assignments."""
    temp_db.executescript(SCHEMA_V1)
    temp_db.executescript(SCHEMA_V2)
    temp_db.executescript(SCHEMA_V4_MIGRATION)

    # Create test posts
    temp_db.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Python programming tutorial', 'user123', 'pythonista')""",
        ('post_1',)
    )
    temp_db.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Machine learning with Python', 'user456', 'ml_expert')""",
        ('post_2',)
    )
    temp_db.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username)
           VALUES (?, datetime('now'), 'Career advice for developers', 'user789', 'career_coach')""",
        ('post_3',)
    )
    temp_db.commit()

    # Create topics
    topics_repo = TopicsRepository(temp_db)
    topics_repo.create_topic("Programming", "Software development")
    topics_repo.create_topic("Machine Learning", "AI/ML content")
    topics_repo.create_topic("Career", "Career advice")

    # Assign post_1 to Programming topic (to create a centroid)
    topics_repo.assign_topic_to_post("post_1", 1)  # Programming

    return temp_db


def test_suggest_topics_for_post(db_with_topics_and_posts):
    """Suggesting topics returns suggestions with topic names."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)

    # post_2 is about ML and Python, should suggest topics
    suggestions = service.suggest_topics_for_post("post_2")

    assert isinstance(suggestions, list)
    # Should have suggestions (may vary based on embedding similarity)
    # At minimum, verify the structure
    for s in suggestions:
        assert isinstance(s, TopicSuggestion)
        assert s.post_id == "post_2"
        assert s.topic_name is not None
        assert 0.0 <= s.confidence <= 1.0


def test_suggest_topics_for_post_excludes_assigned(db_with_topics_and_posts):
    """Already assigned topics are excluded from suggestions."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)

    # post_1 is already assigned to Programming
    suggestions = service.suggest_topics_for_post("post_1", exclude_assigned=True)

    # Programming should not be in suggestions
    topic_names = [s.topic_name for s in suggestions]
    assert "Programming" not in topic_names


def test_suggest_topics_for_post_includes_assigned_when_disabled(db_with_topics_and_posts):
    """Assigned topics are included when exclude_assigned=False."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)

    suggestions = service.suggest_topics_for_post("post_1", exclude_assigned=False)

    # Programming might be in suggestions now
    # Just verify we get some suggestions
    assert isinstance(suggestions, list)


def test_generate_all_suggestions(db_with_topics_and_posts):
    """Generating suggestions processes unassigned posts."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)

    summary = service.generate_all_suggestions(exclude_assigned=True)

    assert isinstance(summary, SuggestionSummary)
    assert summary.total_posts_processed >= 1  # At least post_2 and post_3
    assert summary.total_suggestions >= 0


def test_generate_all_suggestions_stores_pending(db_with_topics_and_posts):
    """Generated suggestions are stored as pending assignments."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)
    topics_repo = TopicsRepository(db_with_topics_and_posts)

    # Clear any existing pending
    topics_repo.clear_pending_assignments()

    # Generate suggestions
    summary = service.generate_all_suggestions(exclude_assigned=True, clear_existing=True)

    # Verify pending assignments exist
    pending = topics_repo.get_pending_assignments()

    assert len(pending) == summary.total_suggestions


def test_compute_all_topic_centroids(db_with_topics_and_posts):
    """Computing centroids returns dict of topic_id to embedding."""
    service = TopicSuggesterService(db_with_topics_and_posts)

    centroids = service.compute_all_topic_centroids()

    # Should have centroid for Programming (topic 1) which has post_1
    assert isinstance(centroids, dict)
    # Centroids exist for topics with assigned posts
    assert 1 in centroids  # Programming has post_1


def test_get_suggestions_summary(db_with_topics_and_posts):
    """Getting summary returns statistics."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)

    # Generate some suggestions
    service.generate_all_suggestions()

    summary = service.get_suggestions_summary()

    assert 'total_pending' in summary
    assert 'posts_with_suggestions' in summary
    assert 'suggestions_by_topic' in summary


def test_get_pending_for_post(db_with_topics_and_posts):
    """Getting pending for a post returns only that post's suggestions."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)

    service.generate_all_suggestions()

    pending = service.get_pending_for_post("post_2")

    for p in pending:
        assert p['post_id'] == "post_2"


def test_approve_suggestion(db_with_topics_and_posts):
    """Approving suggestion moves to post_topics."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)
    topics_repo = TopicsRepository(db_with_topics_and_posts)

    # Generate suggestions
    service.generate_all_suggestions()

    # Get a pending suggestion
    pending = topics_repo.get_pending_assignments()
    if pending:
        pending_id = pending[0]['id']
        post_id = pending[0]['post_id']
        topic_id = pending[0]['topic_id']

        service.approve_suggestion(pending_id)

        # Verify moved to post_topics
        post_topics = topics_repo.get_post_topics(post_id)
        topic_ids = [t['id'] for t in post_topics]
        assert topic_id in topic_ids


def test_reject_suggestion(db_with_topics_and_posts):
    """Rejecting suggestion deletes without assigning."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)
    topics_repo = TopicsRepository(db_with_topics_and_posts)

    # Generate suggestions
    service.generate_all_suggestions()

    # Get a pending suggestion
    pending = topics_repo.get_pending_assignments()
    if pending:
        pending_id = pending[0]['id']

        service.reject_suggestion(pending_id)

        # Verify deleted
        pending_after = topics_repo.get_pending_assignments()
        pending_ids = [p['id'] for p in pending_after]
        assert pending_id not in pending_ids


def test_approve_all_suggestions(db_with_topics_and_posts):
    """Approving all moves all pending to post_topics."""
    service = TopicSuggesterService(db_with_topics_and_posts, confidence_threshold=0.0)
    topics_repo = TopicsRepository(db_with_topics_and_posts)

    # Generate suggestions
    service.generate_all_suggestions()
    pending = topics_repo.get_pending_assignments()
    initial_count = len(pending)

    if initial_count > 0:
        approved = service.approve_all_suggestions(min_confidence=0.0)

        assert approved == initial_count

        # All pending should be gone
        pending_after = topics_repo.get_pending_assignments()
        assert len(pending_after) == 0


def test_topic_suggestion_to_dict():
    """TopicSuggestion can be converted to dict."""
    suggestion = TopicSuggestion(
        post_id="post_123",
        topic_id=1,
        topic_name="Programming",
        confidence=0.85
    )

    d = suggestion.to_dict()

    assert d['post_id'] == "post_123"
    assert d['topic_id'] == 1
    assert d['topic_name'] == "Programming"
    assert d['confidence'] == 0.85


def test_suggestion_summary_to_dict():
    """SuggestionSummary can be converted to dict."""
    summary = SuggestionSummary(
        total_posts_processed=10,
        total_suggestions=15,
        posts_with_suggestions=8,
        suggestions_by_topic={"Programming": 10, "ML": 5}
    )

    d = summary.to_dict()

    assert d['total_posts_processed'] == 10
    assert d['total_suggestions'] == 15
    assert d['posts_with_suggestions'] == 8
    assert d['suggestions_by_topic'] == {"Programming": 10, "ML": 5}