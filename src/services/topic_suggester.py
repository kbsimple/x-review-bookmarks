"""Topic suggester service for hybrid topic assignment.

ORG-03: Application clusters posts into topics using hybrid approach.
ORG-04: User can review and approve AI-suggested topic assignments.

Orchestrates EmbeddingService and ClusteringService to:
1. Compute topic centroids from existing post-topic assignments
2. Generate suggestions for posts without topic assignments
3. Store suggestions as pending assignments for user review
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from .embedding import EmbeddingService
from .clustering import ClusteringService


@dataclass
class TopicSuggestion:
    """A suggested topic assignment for a post."""
    post_id: str
    topic_id: int
    topic_name: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            'post_id': self.post_id,
            'topic_id': self.topic_id,
            'topic_name': self.topic_name,
            'confidence': self.confidence,
        }


@dataclass
class SuggestionSummary:
    """Summary of suggestion generation results."""
    total_posts_processed: int
    total_suggestions: int
    posts_with_suggestions: int
    suggestions_by_topic: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            'total_posts_processed': self.total_posts_processed,
            'total_suggestions': self.total_suggestions,
            'posts_with_suggestions': self.posts_with_suggestions,
            'suggestions_by_topic': self.suggestions_by_topic,
        }


class TopicSuggesterService:
    """Service for generating AI topic suggestions."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        embedding_service: Optional[EmbeddingService] = None,
        clustering_service: Optional[ClusteringService] = None,
        confidence_threshold: float = 0.6,
        max_suggestions: int = 3
    ):
        """Initialize topic suggester.

        Args:
            conn: Database connection.
            embedding_service: Optional EmbeddingService instance.
            clustering_service: Optional ClusteringService instance.
            confidence_threshold: Minimum confidence for suggestions.
            max_suggestions: Max suggestions per post.
        """
        self._conn = conn
        self._embedding = embedding_service or EmbeddingService(conn=conn)
        self._clustering = clustering_service or ClusteringService(
            confidence_threshold=confidence_threshold,
            max_suggestions=max_suggestions
        )

        # Lazy import to avoid circular dependency
        from ..repositories.topics import TopicsRepository
        from ..repositories.posts import PostsRepository
        self._topics_repo = TopicsRepository(conn)
        self._posts_repo = PostsRepository(conn)

    def compute_all_topic_centroids(
        self,
        min_posts_per_topic: int = 1
    ) -> dict[int, np.ndarray]:
        """Compute centroids for all topics with assigned posts.

        Args:
            min_posts_per_topic: Minimum posts for centroid computation.

        Returns:
            Dict mapping topic_id to centroid embedding.
        """
        topics = self._topics_repo.list_topics()
        topic_embeddings: dict[int, list[np.ndarray]] = {}

        for topic in topics:
            topic_id = topic['id']
            post_ids = self._topics_repo.get_posts_by_topic(topic_id)

            if not post_ids:
                continue

            # Get posts and their embeddings
            posts = []
            for post_id in post_ids:
                post = self._posts_repo.get_by_id(post_id)
                if post:
                    posts.append(post)

            if len(posts) >= min_posts_per_topic:
                # Get embeddings (cached if available)
                _, embeddings = self._embedding.get_embeddings_for_posts(posts, self._conn)
                topic_embeddings[topic_id] = [embeddings[i] for i in range(len(posts))]

        return self._clustering.compute_topic_centroids(topic_embeddings, min_posts=min_posts_per_topic)

    def suggest_topics_for_post(
        self,
        post_id: str,
        topic_centroids: Optional[dict[int, np.ndarray]] = None,
        exclude_assigned: bool = True
    ) -> list[TopicSuggestion]:
        """Suggest topics for a single post.

        Args:
            post_id: X post ID.
            topic_centroids: Pre-computed topic centroids (computed if None).
            exclude_assigned: Exclude topics already assigned to this post.

        Returns:
            List of TopicSuggestion objects.
        """
        # Get post
        post = self._posts_repo.get_by_id(post_id)
        if not post:
            return []

        # Get embedding
        embedding = self._embedding.get_or_create_embedding(
            post_id,
            self._embedding.create_enriched_text(post),
            self._conn
        )

        # Get centroids
        if topic_centroids is None:
            topic_centroids = self.compute_all_topic_centroids()

        # Get excluded topics
        excluded_ids: set[int] = set()
        if exclude_assigned:
            assigned = self._topics_repo.get_post_topics(post_id)
            excluded_ids = {t['id'] for t in assigned}

        # Get suggestions
        suggestions = self._clustering.suggest_topics(embedding, topic_centroids, excluded_ids)

        # Build result with topic names
        result = []
        for topic_id, confidence in suggestions:
            topic = self._topics_repo.get_topic_by_id(topic_id)
            if topic:
                result.append(TopicSuggestion(
                    post_id=post_id,
                    topic_id=topic_id,
                    topic_name=topic['name'],
                    confidence=confidence
                ))

        return result

    def generate_all_suggestions(
        self,
        topic_centroids: Optional[dict[int, np.ndarray]] = None,
        exclude_assigned: bool = True,
        clear_existing: bool = True,
        show_progress: bool = False
    ) -> SuggestionSummary:
        """Generate suggestions for all posts without topic assignments.

        Args:
            topic_centroids: Pre-computed topic centroids.
            exclude_assigned: Skip posts that already have topic assignments.
            clear_existing: Clear existing pending suggestions first.
            show_progress: Show progress bar.

        Returns:
            SuggestionSummary with statistics.
        """
        # Clear existing pending suggestions
        if clear_existing:
            self._topics_repo.clear_pending_assignments()

        # Compute centroids if not provided
        if topic_centroids is None:
            topic_centroids = self.compute_all_topic_centroids()

        if not topic_centroids:
            # No topics with posts, nothing to suggest
            return SuggestionSummary(
                total_posts_processed=0,
                total_suggestions=0,
                posts_with_suggestions=0,
                suggestions_by_topic={}
            )

        # Get posts to process
        all_posts = self._posts_repo.get_all(limit=1000, offset=0)

        if exclude_assigned:
            # Filter out posts that already have topic assignments
            unassigned_posts = []
            for post in all_posts:
                topics = self._topics_repo.get_post_topics(post['x_post_id'])
                if not topics:
                    unassigned_posts.append(post)
            posts_to_process = unassigned_posts
        else:
            posts_to_process = all_posts

        # Process each post
        total_suggestions = 0
        posts_with_suggestions = 0
        suggestions_by_topic: dict[str, int] = {}

        for post in posts_to_process:
            suggestions = self.suggest_topics_for_post(
                post['x_post_id'],
                topic_centroids=topic_centroids,
                exclude_assigned=exclude_assigned
            )

            if suggestions:
                posts_with_suggestions += 1

                for suggestion in suggestions:
                    # Store as pending assignment
                    self._topics_repo.create_pending_assignment(
                        post_id=suggestion.post_id,
                        topic_id=suggestion.topic_id,
                        confidence=suggestion.confidence
                    )
                    total_suggestions += 1

                    # Track by topic
                    topic_name = suggestion.topic_name
                    suggestions_by_topic[topic_name] = suggestions_by_topic.get(topic_name, 0) + 1

        return SuggestionSummary(
            total_posts_processed=len(posts_to_process),
            total_suggestions=total_suggestions,
            posts_with_suggestions=posts_with_suggestions,
            suggestions_by_topic=suggestions_by_topic
        )

    def get_suggestions_summary(self) -> dict[str, Any]:
        """Get summary of current pending suggestions.

        Returns:
            Dict with counts and statistics.
        """
        pending = self._topics_repo.get_pending_assignments()

        posts_with_suggestions = len(set(p['post_id'] for p in pending))

        suggestions_by_topic: dict[str, int] = {}
        for p in pending:
            topic_name = p.get('topic_name', 'Unknown')
            suggestions_by_topic[topic_name] = suggestions_by_topic.get(topic_name, 0) + 1

        return {
            'total_pending': len(pending),
            'posts_with_suggestions': posts_with_suggestions,
            'suggestions_by_topic': suggestions_by_topic,
        }

    def get_pending_for_post(self, post_id: str) -> list[dict[str, Any]]:
        """Get pending suggestions for a specific post.

        Args:
            post_id: X post ID.

        Returns:
            List of pending suggestion dicts.
        """
        return self._topics_repo.get_pending_assignments(post_id=post_id)

    def approve_suggestion(self, pending_id: int) -> None:
        """Approve a pending suggestion.

        Args:
            pending_id: Pending assignment ID.
        """
        self._topics_repo.approve_pending_assignment(pending_id)

    def reject_suggestion(self, pending_id: int) -> None:
        """Reject a pending suggestion.

        Args:
            pending_id: Pending assignment ID.
        """
        self._topics_repo.reject_pending_assignment(pending_id)

    def approve_all_suggestions(self, min_confidence: float = 0.0) -> int:
        """Approve all pending suggestions above confidence threshold.

        Args:
            min_confidence: Minimum confidence to auto-approve.

        Returns:
            Number of suggestions approved.
        """
        pending = self._topics_repo.get_pending_assignments()
        approved = 0

        for p in pending:
            if p['confidence'] >= min_confidence:
                self._topics_repo.approve_pending_assignment(p['id'])
                approved += 1

        return approved