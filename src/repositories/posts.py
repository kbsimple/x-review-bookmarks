"""Posts repository for database operations.

DATA-02: Store posts with full content (text, author, images, links, media).
DATA-03: Store publication date for each post.

Usage:
    from src.repositories import PostsRepository
    from src.db import get_connection

    conn = get_connection()
    repo = PostsRepository(conn)
    repo.insert_post({...})
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


class PostsRepository:
    """Repository for posts table CRUD operations.

    Handles all database operations for the posts table:
    - Insert/upsert posts with full content
    - Query posts by ID, author, date range
    - Count posts for sync summary
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize repository with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn

    def insert_post(self, post: dict[str, Any]) -> None:
        """Insert a new post into the database.

        Args:
            post: Dict with keys matching posts table columns.
                  Required: x_post_id, created_at, text, author_id, author_username
                  Optional: author_display_name, media_urls, link_urls, bookmarked_at

        Raises:
            sqlite3.IntegrityError: If x_post_id already exists.
        """
        self._conn.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username,
                author_display_name, media_urls, link_urls, bookmarked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                post.get('bookmarked_at'),
            )
        )
        self._conn.commit()

    def upsert_post(self, post: dict[str, Any]) -> None:
        """Insert or update a post.

        If x_post_id exists, updates all fields except fetched_at.
        If not exists, inserts as new post.

        Args:
            post: Dict with post data (same as insert_post).
        """
        self._conn.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username,
                author_display_name, media_urls, link_urls, bookmarked_at, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(x_post_id) DO UPDATE SET
                created_at = excluded.created_at,
                text = excluded.text,
                author_id = excluded.author_id,
                author_username = excluded.author_username,
                author_display_name = excluded.author_display_name,
                media_urls = excluded.media_urls,
                link_urls = excluded.link_urls,
                bookmarked_at = excluded.bookmarked_at,
                note = excluded.note,
                sync_version = sync_version + 1
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
                post.get('bookmarked_at'),
                post.get('note'),
            )
        )
        self._conn.commit()

    def get_by_id(self, x_post_id: str) -> Optional[dict[str, Any]]:
        """Get a post by x_post_id.

        Args:
            x_post_id: The X post ID.

        Returns:
            Dict with post data, or None if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM posts WHERE x_post_id = ?",
            (x_post_id,)
        ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Get all posts ordered by created_at descending.

        Args:
            limit: Maximum posts to return.
            offset: Offset for pagination.

        Returns:
            List of post dicts.
        """
        rows = self._conn.execute(
            "SELECT * FROM posts ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def count(self) -> int:
        """Get total post count.

        Returns:
            Number of posts in database.
        """
        row = self._conn.execute("SELECT COUNT(*) as count FROM posts").fetchone()
        return row['count'] if row else 0

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert a database row to dict, parsing JSON fields."""
        return {
            'x_post_id': row['x_post_id'],
            'created_at': row['created_at'],
            'text': row['text'],
            'author_id': row['author_id'],
            'author_username': row['author_username'],
            'author_display_name': row['author_display_name'],
            'media_urls': json.loads(row['media_urls']) if row['media_urls'] else [],
            'link_urls': json.loads(row['link_urls']) if row['link_urls'] else [],
            'bookmarked_at': row['bookmarked_at'],
            'fetched_at': row['fetched_at'],
            'sync_version': row['sync_version'],
            'note': row['note'] if 'note' in row.keys() else None,
            'link_status': row['link_status'] if 'link_status' in row.keys() else 'unchecked',
        }

    def update_note(self, x_post_id: str, note: Optional[str]) -> None:
        """Update or clear the note for a post.

        NOTE-01: User can add personal notes to bookmarked posts.
        NOTE-02: Notes displayed when post is resurfaced for review.

        Args:
            x_post_id: The X post ID.
            note: Note text, or None to clear the note.
        """
        self._conn.execute(
            "UPDATE posts SET note = ? WHERE x_post_id = ?",
            (note, x_post_id)
        )
        self._conn.commit()

    def update_link_status(self, x_post_id: str, status: str) -> None:
        """Update the link status for a post.

        MAINT-01: Application detects and flags dead links.
        MAINT-02: Application can filter dead links from review queue.

        Args:
            x_post_id: The X post ID.
            status: Link status value:
                     - "ok": All links verified as working
                     - "dead": At least one link is dead
                     - "error": Error checking links
                     - "unchecked": Not yet checked (default)
                     - ISO timestamp: Last check time for re-check scheduling
        """
        self._conn.execute(
            "UPDATE posts SET link_status = ? WHERE x_post_id = ?",
            (status, x_post_id)
        )
        self._conn.commit()

    def get_posts_with_links(self) -> list[dict[str, Any]]:
        """Get all posts that have link URLs.

        MAINT-01: Application needs to check links in stored posts.

        Returns:
            List of posts where link_urls is not empty.
            Ordered by created_at descending.
        """
        rows = self._conn.execute(
            """SELECT * FROM posts
               WHERE link_urls IS NOT NULL
                 AND link_urls != '[]'
                 AND json_array_length(link_urls) > 0
               ORDER BY created_at DESC"""
        ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def get_posts_exclude_dead_links(self) -> list[dict[str, Any]]:
        """Get posts excluding those with dead links.

        MAINT-02: Application can filter dead links from review queue.

        Returns:
            List of posts where link_status is not 'dead'.
            Ordered by created_at descending.
        """
        rows = self._conn.execute(
            """SELECT * FROM posts
               WHERE link_status IS NULL
                  OR link_status != 'dead'
               ORDER BY created_at DESC"""
        ).fetchall()

        return [self._row_to_dict(row) for row in rows]