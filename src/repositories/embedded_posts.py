"""Embedded posts repository for database operations.

STR-01: Embedded posts stored in separate embedded_posts table.
STR-03: Unavailable originals marked with available=False.

This repository handles CRUD operations for embedded posts, which store
the original tweet content for retweets and quote tweets.

Usage:
    from src.repositories.embedded_posts import EmbeddedPostsRepository
    from src.db import get_connection

    conn = get_connection()
    repo = EmbeddedPostsRepository(conn)
    repo.upsert_embedded_post({...})
    embedded = repo.get_by_id("tweet_123")
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


class EmbeddedPostsRepository:
    """Repository for embedded_posts table CRUD operations.

    Handles all database operations for the embedded_posts table:
    - Upsert embedded posts (insert new or update existing on conflict)
    - Query embedded posts by ID
    - Handle unavailable flag for deleted/protected originals

    STR-01: Embedded posts stored in separate embedded_posts table.
    STR-03: Unavailable originals marked with available=False.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn

    def upsert_embedded_post(self, post: dict[str, Any]) -> None:
        """Insert or update an embedded post.

        If x_post_id exists, updates all fields.
        If not exists, inserts as new embedded post.

        STR-01: Store embedded post content in embedded_posts table.
        STR-03: Handle available flag for deleted/protected originals.

        Args:
            post: Dict with embedded post data.
                  Required: x_post_id, created_at, text, author_id, author_username
                  Optional: author_display_name, media_urls, link_urls, available
                            available defaults to True if not provided.
        """
        # Convert available boolean to INTEGER for SQLite
        available_int = 1 if post.get('available', True) else 0

        self._conn.execute(
            """
            INSERT INTO embedded_posts (
                x_post_id, created_at, text, author_id, author_username,
                author_display_name, media_urls, link_urls, available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(x_post_id) DO UPDATE SET
                created_at = excluded.created_at,
                text = excluded.text,
                author_id = excluded.author_id,
                author_username = excluded.author_username,
                author_display_name = excluded.author_display_name,
                media_urls = excluded.media_urls,
                link_urls = excluded.link_urls,
                available = excluded.available
            """,
            (
                post['x_post_id'],
                post['created_at'],
                post['text'],
                post['author_id'],
                post['author_username'],
                post.get('author_display_name'),
                json.dumps(post.get('media_urls', [])),
                json.dumps(post.get('link_urls', [])),
                available_int,
            )
        )
        self._conn.commit()

    def get_by_id(self, x_post_id: str) -> Optional[dict[str, Any]]:
        """Get an embedded post by x_post_id.

        Args:
            x_post_id: The X post ID.

        Returns:
            Dict with embedded post data, or None if not found.
            The 'available' field is returned as bool (converted from INTEGER).
        """
        row = self._conn.execute(
            "SELECT * FROM embedded_posts WHERE x_post_id = ?",
            (x_post_id,)
        ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert a database row to dict, parsing JSON fields and converting available to bool.

        Args:
            row: SQLite Row object.

        Returns:
            Dict with embedded post data.
            The 'available' field is converted from INTEGER to bool.
        """
        return {
            'x_post_id': row['x_post_id'],
            'created_at': row['created_at'],
            'text': row['text'],
            'author_id': row['author_id'],
            'author_username': row['author_username'],
            'author_display_name': row['author_display_name'],
            'media_urls': json.loads(row['media_urls']) if row['media_urls'] else [],
            'link_urls': json.loads(row['link_urls']) if row['link_urls'] else [],
            'available': bool(row['available']),
        }