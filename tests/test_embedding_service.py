"""Tests for EmbeddingService.

ORG-03: Application clusters posts into topics using embeddings.
"""

import pytest
import numpy as np
from src.services.embedding import EmbeddingService
from src.db.schema import SCHEMA_V1, SCHEMA_V2, SCHEMA_V4_MIGRATION


@pytest.fixture
def db_with_embeddings(temp_db):
    """Create database with embeddings tables and test post."""
    temp_db.executescript(SCHEMA_V1)
    temp_db.executescript(SCHEMA_V2)
    temp_db.executescript(SCHEMA_V4_MIGRATION)

    temp_db.execute(
        """INSERT INTO posts (x_post_id, created_at, text, author_id, author_username, author_display_name)
           VALUES (?, datetime('now'), 'Python programming tutorial', 'user123', 'pythonista', 'Python Expert')""",
        ('post_123',)
    )
    temp_db.commit()
    return temp_db


def test_generate_embedding_shape():
    """Generated embedding has 384 dimensions."""
    service = EmbeddingService()
    embedding = service.generate_embedding("Hello world")

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)
    assert embedding.dtype == np.float32 or embedding.dtype == np.float64


def test_generate_embedding_deterministic():
    """Same input produces same embedding."""
    service = EmbeddingService()
    emb1 = service.generate_embedding("Hello world")
    emb2 = service.generate_embedding("Hello world")

    np.testing.assert_array_almost_equal(emb1, emb2)


def test_generate_embeddings_batch():
    """Batch generation produces correct number of embeddings."""
    service = EmbeddingService()
    texts = ["Hello", "World", "Test"]
    embeddings = service.generate_embeddings(texts)

    assert embeddings.shape == (3, 384)


def test_get_or_create_embedding_caches(db_with_embeddings):
    """Embedding is cached in database."""
    service = EmbeddingService(conn=db_with_embeddings)

    embedding = service.get_or_create_embedding(
        "post_123",
        "Python programming tutorial"
    )

    # Check database has the embedding
    row = db_with_embeddings.execute(
        "SELECT embedding FROM post_embeddings WHERE post_id = ?",
        ('post_123',)
    ).fetchone()

    assert row is not None
    cached = np.frombuffer(row['embedding'], dtype=np.float32)
    np.testing.assert_array_almost_equal(embedding, cached)


def test_get_or_create_embedding_retrieves_cached(db_with_embeddings):
    """Cached embedding is retrieved instead of regenerated."""
    service = EmbeddingService(conn=db_with_embeddings)

    # First call caches
    emb1 = service.get_or_create_embedding("post_123", "Python programming tutorial")

    # Modify the text - should still return cached
    emb2 = service.get_or_create_embedding("post_123", "Completely different text")

    # Should be identical (cached)
    np.testing.assert_array_almost_equal(emb1, emb2)


def test_create_enriched_text():
    """Enriched text combines post content with author context."""
    service = EmbeddingService()

    post = {
        'text': 'Python is great',
        'author_username': 'pythonista',
        'author_display_name': 'Python Expert'
    }

    enriched = service.create_enriched_text(post)

    assert 'Python is great' in enriched
    assert '@pythonista' in enriched
    assert 'Python Expert' in enriched


def test_create_enriched_text_minimal():
    """Enriched text works with minimal post data."""
    service = EmbeddingService()

    post = {'text': 'Just text'}

    enriched = service.create_enriched_text(post)

    assert enriched == 'Just text'


def test_get_embeddings_for_posts(db_with_embeddings):
    """Batch embedding retrieval for posts."""
    service = EmbeddingService(conn=db_with_embeddings)

    posts = [
        {
            'x_post_id': 'post_123',
            'text': 'Python programming',
            'author_username': 'pythonista'
        }
    ]

    post_ids, embeddings = service.get_embeddings_for_posts(posts)

    assert len(post_ids) == 1
    assert post_ids[0] == 'post_123'
    assert embeddings.shape == (1, 384)


def test_clear_cache(db_with_embeddings):
    """Clearing cache removes embeddings."""
    service = EmbeddingService(conn=db_with_embeddings)

    # Create embedding
    service.get_or_create_embedding("post_123", "Test")

    # Clear cache
    count = service.clear_cache()

    assert count == 1

    # Verify cleared
    row = db_with_embeddings.execute(
        "SELECT * FROM post_embeddings WHERE post_id = ?",
        ('post_123',)
    ).fetchone()
    assert row is None