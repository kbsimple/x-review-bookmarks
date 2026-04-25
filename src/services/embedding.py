"""Embedding service for generating and caching text embeddings.

ORG-03: Application clusters posts into topics using embeddings.

Uses sentence-transformers with all-MiniLM-L6-v2 model:
- 384-dimensional embeddings
- Fast inference (~22M params)
- Works well on short text (tweets)

Usage:
    from src.services.embedding import EmbeddingService

    service = EmbeddingService()
    embedding = service.generate_embedding("Hello world")
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Service for generating and caching text embeddings."""

    DEFAULT_MODEL = 'all-MiniLM-L6-v2'

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        conn: Optional[sqlite3.Connection] = None
    ):
        """Initialize embedding service.

        Args:
            model_name: Name of sentence-transformers model.
            conn: Optional database connection for caching.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self._conn = conn

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            384-dimensional numpy array (float32).
        """
        return self.model.encode(text, convert_to_numpy=True)

    def generate_embeddings(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        """Generate embeddings for multiple texts.

        Batch processing is more efficient than individual calls.

        Args:
            texts: List of texts to embed.
            show_progress: Show progress bar.

        Returns:
            2D numpy array of shape (len(texts), 384).
        """
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress
        )

    def get_or_create_embedding(
        self,
        post_id: str,
        text: str,
        conn: Optional[sqlite3.Connection] = None
    ) -> np.ndarray:
        """Get cached embedding or generate and cache new one.

        Args:
            post_id: X post ID.
            text: Text to embed if not cached.
            conn: Database connection (uses self._conn if not provided).

        Returns:
            384-dimensional numpy array.
        """
        conn = conn or self._conn
        if conn is None:
            # No caching, just generate
            return self.generate_embedding(text)

        # Check cache
        row = conn.execute(
            "SELECT embedding, model_name FROM post_embeddings WHERE post_id = ?",
            (post_id,)
        ).fetchone()

        if row and row['model_name'] == self.model_name:
            # Return cached embedding
            return np.frombuffer(row['embedding'], dtype=np.float32).copy()

        # Generate new embedding
        embedding = self.generate_embedding(text)

        # Cache it
        conn.execute(
            """INSERT OR REPLACE INTO post_embeddings (post_id, embedding, model_name)
               VALUES (?, ?, ?)""",
            (post_id, embedding.astype(np.float32).tobytes(), self.model_name)
        )
        conn.commit()

        return embedding

    def create_enriched_text(self, post: dict) -> str:
        """Create enriched text for embedding from post data.

        Combines post text with author context for better embeddings.
        Short text (tweets) benefits from additional context.

        Args:
            post: Post dict with 'text', 'author_username', 'author_display_name'.

        Returns:
            Enriched text string.
        """
        parts = [post.get('text', '')]

        if post.get('author_username'):
            parts.append(f"by @{post['author_username']}")

        if post.get('author_display_name'):
            parts.append(f"({post['author_display_name']})")

        return " ".join(parts)

    def get_embeddings_for_posts(
        self,
        posts: list[dict],
        conn: Optional[sqlite3.Connection] = None,
        show_progress: bool = False
    ) -> tuple[list[str], np.ndarray]:
        """Get embeddings for multiple posts.

        Fetches cached embeddings where available, generates new ones otherwise.

        Args:
            posts: List of post dicts with 'x_post_id', 'text', etc.
            conn: Database connection for caching.
            show_progress: Show progress bar.

        Returns:
            Tuple of (post_ids, embeddings) where embeddings is 2D array.
        """
        conn = conn or self._conn
        post_ids = []
        embeddings = []

        # Collect posts needing embedding
        texts_to_embed = []
        ids_to_embed = []

        for post in posts:
            post_id = post['x_post_id']
            enriched_text = self.create_enriched_text(post)

            if conn:
                row = conn.execute(
                    "SELECT embedding, model_name FROM post_embeddings WHERE post_id = ?",
                    (post_id,)
                ).fetchone()

                if row and row['model_name'] == self.model_name:
                    # Use cached
                    post_ids.append(post_id)
                    embeddings.append(np.frombuffer(row['embedding'], dtype=np.float32).copy())
                    continue

            # Need to embed
            ids_to_embed.append(post_id)
            texts_to_embed.append(enriched_text)

        # Batch embed new posts
        if texts_to_embed:
            new_embeddings = self.generate_embeddings(texts_to_embed, show_progress=show_progress)

            for i, (post_id, embedding) in enumerate(zip(ids_to_embed, new_embeddings)):
                post_ids.append(post_id)
                embeddings.append(embedding)

                # Cache if we have connection
                if conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO post_embeddings (post_id, embedding, model_name)
                           VALUES (?, ?, ?)""",
                        (post_id, embedding.astype(np.float32).tobytes(), self.model_name)
                    )

            if conn:
                conn.commit()

        return post_ids, np.array(embeddings)

    def clear_cache(self, conn: Optional[sqlite3.Connection] = None) -> int:
        """Clear all cached embeddings.

        Useful when changing models or re-generating embeddings.

        Args:
            conn: Database connection.

        Returns:
            Number of embeddings cleared.
        """
        conn = conn or self._conn
        if conn is None:
            return 0

        cursor = conn.execute("DELETE FROM post_embeddings")
        conn.commit()
        return cursor.rowcount