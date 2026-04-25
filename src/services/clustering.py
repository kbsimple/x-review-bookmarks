"""Clustering service for topic matching and suggestions.

ORG-03: Application clusters posts into topics using hybrid approach.

Uses K-Means clustering and cosine similarity for topic matching.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity


class ClusteringService:
    """Service for clustering posts and matching to topics."""

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        max_suggestions: int = 3
    ):
        """Initialize clustering service.

        Args:
            confidence_threshold: Minimum cosine similarity for suggestion (0.0-1.0).
            max_suggestions: Maximum topics to suggest per post.
        """
        self.confidence_threshold = confidence_threshold
        self.max_suggestions = max_suggestions

    def compute_topic_centroids(
        self,
        topic_posts: dict[int, list[np.ndarray]],
        min_posts: int = 1
    ) -> dict[int, np.ndarray]:
        """Compute centroid embedding for each topic.

        Args:
            topic_posts: Dict mapping topic_id to list of embeddings.
            min_posts: Minimum posts required to compute centroid.

        Returns:
            Dict mapping topic_id to centroid embedding.
        """
        centroids = {}

        for topic_id, embeddings in topic_posts.items():
            if len(embeddings) >= min_posts:
                centroids[topic_id] = np.mean(embeddings, axis=0)

        return centroids

    def suggest_topics(
        self,
        post_embedding: np.ndarray,
        topic_centroids: dict[int, np.ndarray],
        excluded_topic_ids: Optional[set[int]] = None
    ) -> list[tuple[int, float]]:
        """Suggest topics based on cosine similarity to topic centroids.

        Args:
            post_embedding: 384-dim embedding of the post.
            topic_centroids: Dict mapping topic_id to centroid embedding.
            excluded_topic_ids: Topic IDs to exclude from suggestions.

        Returns:
            List of (topic_id, confidence) sorted by confidence descending.
        """
        excluded = excluded_topic_ids or set()
        similarities = []

        post_emb = post_embedding.reshape(1, -1)

        for topic_id, centroid in topic_centroids.items():
            if topic_id in excluded:
                continue

            # Cosine similarity
            centroid_emb = centroid.reshape(1, -1)
            sim = cosine_similarity(post_emb, centroid_emb)[0][0]

            if sim >= self.confidence_threshold:
                similarities.append((int(topic_id), float(sim)))

        # Sort by confidence descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:self.max_suggestions]

    def cluster_posts(
        self,
        embeddings: np.ndarray,
        n_clusters: Optional[int] = None,
        min_clusters: int = 5,
        max_clusters: int = 20,
        random_state: int = 42
    ) -> tuple[np.ndarray, float]:
        """Cluster post embeddings using K-Means.

        Args:
            embeddings: 2D array of embeddings (n_posts, 384).
            n_clusters: Number of clusters. If None, finds optimal via silhouette.
            min_clusters: Minimum clusters when auto-detecting.
            max_clusters: Maximum clusters when auto-detecting.
            random_state: Random seed for reproducibility.

        Returns:
            Tuple of (cluster_labels, silhouette_score).
        """
        if n_clusters is None:
            # Find optimal cluster count via silhouette
            best_score = -1
            best_n = min_clusters
            best_labels = None

            # Cap max_clusters at n_samples - 1
            max_n = min(max_clusters, len(embeddings) - 1)

            for n in range(min_clusters, max_n + 1):
                kmeans = KMeans(
                    n_clusters=n,
                    n_init=5,
                    random_state=random_state
                )
                labels = kmeans.fit_predict(embeddings)

                # Need at least 2 clusters for silhouette
                if len(set(labels)) >= 2:
                    score = silhouette_score(embeddings, labels)

                    if score > best_score:
                        best_score = score
                        best_n = n
                        best_labels = labels

            if best_labels is not None:
                return best_labels, best_score

        # Use specified n_clusters
        n = n_clusters or min_clusters
        kmeans = KMeans(n_clusters=n, n_init=5, random_state=random_state)
        labels = kmeans.fit_predict(embeddings)

        # Calculate silhouette if we have enough clusters
        if len(set(labels)) >= 2:
            score = silhouette_score(embeddings, labels)
        else:
            score = 0.0

        return labels, score

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding.
            embedding2: Second embedding.

        Returns:
            Similarity score (0.0-1.0).
        """
        e1 = embedding1.reshape(1, -1)
        e2 = embedding2.reshape(1, -1)
        return float(cosine_similarity(e1, e2)[0][0])