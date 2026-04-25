"""Tests for ClusteringService.

ORG-03: Application clusters posts into topics using clustering.
"""

import pytest
import numpy as np
from src.services.clustering import ClusteringService


def test_compute_topic_centroids():
    """Centroids are computed as mean of embeddings."""
    service = ClusteringService()

    # Two topics with sample embeddings
    topic_posts = {
        1: [np.random.rand(384).astype(np.float32) for _ in range(5)],
        2: [np.random.rand(384).astype(np.float32) for _ in range(3)],
    }

    centroids = service.compute_topic_centroids(topic_posts)

    assert len(centroids) == 2
    assert 1 in centroids
    assert 2 in centroids
    assert centroids[1].shape == (384,)


def test_compute_topic_centroids_min_posts():
    """Topics with fewer than min_posts are excluded."""
    service = ClusteringService()

    topic_posts = {
        1: [np.random.rand(384) for _ in range(5)],
        2: [np.random.rand(384) for _ in range(1)],  # Too few
    }

    centroids = service.compute_topic_centroids(topic_posts, min_posts=2)

    assert len(centroids) == 1
    assert 1 in centroids
    assert 2 not in centroids


def test_suggest_topics_returns_sorted():
    """Suggestions are sorted by confidence descending."""
    service = ClusteringService(confidence_threshold=0.0, max_suggestions=5)

    # Create post embedding
    post_emb = np.random.rand(384).astype(np.float32)

    # Create centroids (different distances)
    centroids = {
        1: post_emb + 0.1,  # Similar
        2: post_emb + 0.5,  # Less similar
        3: post_emb + 0.2,  # Medium
    }

    suggestions = service.suggest_topics(post_emb, centroids)

    # Should be sorted by confidence
    confidences = [s[1] for s in suggestions]
    assert confidences == sorted(confidences, reverse=True)


def test_suggest_topics_respects_threshold():
    """Suggestions below threshold are filtered out."""
    service = ClusteringService(confidence_threshold=0.9, max_suggestions=5)

    post_emb = np.ones(384, dtype=np.float32)
    post_emb = post_emb / np.linalg.norm(post_emb)  # Normalize

    centroids = {
        1: np.ones(384, dtype=np.float32) / np.sqrt(384),  # Identical (sim=1.0)
        2: np.zeros(384, dtype=np.float32),  # Orthogonal (sim=0.0)
    }

    suggestions = service.suggest_topics(post_emb, centroids)

    # Only topic 1 should pass threshold
    assert len(suggestions) == 1
    assert suggestions[0][0] == 1


def test_suggest_topics_respects_max():
    """Suggestions are limited to max_suggestions."""
    service = ClusteringService(confidence_threshold=0.0, max_suggestions=2)

    post_emb = np.random.rand(384).astype(np.float32)
    centroids = {i: np.random.rand(384).astype(np.float32) for i in range(10)}

    suggestions = service.suggest_topics(post_emb, centroids)

    assert len(suggestions) <= 2


def test_suggest_topics_excludes_ids():
    """Excluded topic IDs are not suggested."""
    service = ClusteringService(confidence_threshold=0.0, max_suggestions=5)

    post_emb = np.ones(384, dtype=np.float32)
    centroids = {
        1: post_emb.copy(),
        2: post_emb.copy(),
        3: post_emb.copy(),
    }

    suggestions = service.suggest_topics(post_emb, centroids, excluded_topic_ids={1, 2})

    topic_ids = [s[0] for s in suggestions]
    assert 1 not in topic_ids
    assert 2 not in topic_ids
    assert 3 in topic_ids


def test_cluster_posts():
    """Clustering produces valid labels."""
    service = ClusteringService()

    # Generate sample embeddings
    embeddings = np.random.rand(50, 384).astype(np.float32)

    labels, score = service.cluster_posts(embeddings, n_clusters=5)

    assert labels.shape == (50,)
    assert len(set(labels)) == 5
    assert -1 <= score <= 1  # Silhouette score range


def test_cluster_posts_auto_detect():
    """Auto-detect finds optimal cluster count."""
    service = ClusteringService()

    embeddings = np.random.rand(30, 384).astype(np.float32)

    labels, score = service.cluster_posts(embeddings, n_clusters=None, min_clusters=2, max_clusters=5)

    assert labels.shape == (30,)
    assert 2 <= len(set(labels)) <= 5


def test_compute_similarity():
    """Similarity calculation is correct."""
    service = ClusteringService()

    # Identical embeddings should have similarity 1.0
    e1 = np.ones(384, dtype=np.float32)
    e1 = e1 / np.linalg.norm(e1)

    sim = service.compute_similarity(e1, e1)
    assert abs(sim - 1.0) < 0.01

    # Orthogonal embeddings should have similarity 0.0
    e_orth = np.zeros(384, dtype=np.float32)
    e_orth[0] = 1.0
    e_other = np.zeros(384, dtype=np.float32)
    e_other[1] = 1.0

    sim = service.compute_similarity(e_orth, e_other)
    assert abs(sim - 0.0) < 0.01