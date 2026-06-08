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

        STR-02: Includes post_type and embedded_post_id columns.

        Args:
            post: Dict with post data (same as insert_post).
        """
        self._conn.execute(
            """
            INSERT INTO posts (
                x_post_id, created_at, text, author_id, author_username,
                author_display_name, media_urls, link_urls, bookmarked_at, note,
                post_type, embedded_post_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                post_type = excluded.post_type,
                embedded_post_id = excluded.embedded_post_id,
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
                post.get('post_type', 'original'),
                post.get('embedded_post_id'),
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

    def get_by_id_with_embedded(self, x_post_id: str) -> Optional[dict[str, Any]]:
        """Get a post by x_post_id with embedded post data for retweets/quotes.

        WEB-07, WEB-08, CAST-06, CAST-07, CAST-08: Include embedded post data.
        Returns post with 'embedded_post' key populated for retweets/quotes.

        Args:
            x_post_id: The X post ID.

        Returns:
            Dict with post data and 'embedded_post' key (None for original posts),
            or None if not found.
        """
        query = """
            SELECT p.*,
                   e.x_post_id as embedded_id,
                   e.created_at as embedded_created_at,
                   e.text as embedded_text,
                   e.author_id as embedded_author_id,
                   e.author_username as embedded_author_username,
                   e.author_display_name as embedded_author_display_name,
                   e.media_urls as embedded_media_urls,
                   e.link_urls as embedded_link_urls,
                   e.available as embedded_available
            FROM posts p
            LEFT JOIN embedded_posts e ON p.embedded_post_id = e.x_post_id
            WHERE p.x_post_id = ?
        """
        row = self._conn.execute(query, (x_post_id,)).fetchone()

        if row is None:
            return None

        return self._row_to_dict_with_embedded(row)

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

    def get_all_ordered(
        self,
        order: str = "newest",
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get all posts with specified ordering.

        Args:
            order: Sort order - "newest", "oldest", or "random".
            limit: Maximum posts to return.
            offset: Offset for pagination.

        Returns:
            List of post dicts.
        """
        order_clause = {
            "newest": "ORDER BY created_at DESC",
            "oldest": "ORDER BY created_at ASC",
            "random": "ORDER BY RANDOM()",
        }.get(order, "ORDER BY created_at DESC")

        rows = self._conn.execute(
            f"SELECT * FROM posts {order_clause} LIMIT ? OFFSET ?",
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
            'post_type': row['post_type'] if 'post_type' in row.keys() else 'original',
            'embedded_post_id': row['embedded_post_id'] if 'embedded_post_id' in row.keys() else None,
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

    def get_post_stats(self) -> dict[str, Any]:
        """Get post statistics for display.

        Returns aggregate statistics about posts:
        - oldest_date: Date of oldest post
        - newest_date: Date of newest post
        - total: Total number of posts
        - by_month: Dict mapping YYYY-MM to count

        Returns:
            Dict with statistics.
        """
        # Get date range and total
        row = self._conn.execute(
            """SELECT
                MIN(created_at) as oldest,
                MAX(created_at) as newest,
                COUNT(*) as total
               FROM posts"""
        ).fetchone()

        result = {
            'oldest_date': row['oldest'][:10] if row['oldest'] else None,
            'newest_date': row['newest'][:10] if row['newest'] else None,
            'total': row['total'] if row else 0,
            'by_month': {}
        }

        if row['total'] == 0:
            return result

        # Get posts by month
        rows = self._conn.execute(
            """SELECT
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as count
               FROM posts
               GROUP BY month
               ORDER BY month DESC"""
        ).fetchall()

        result['by_month'] = {r['month']: r['count'] for r in rows}

        return result

    def get_paginated(
        self,
        limit: int = 20,
        after_created_at: Optional[str] = None,
        after_post_id: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Get posts with cursor-based pagination.

        WEB-04: User can browse posts with cursor-based pagination.

        Returns posts ordered by created_at DESC, x_post_id DESC for stable
        pagination. The cursor is (created_at, x_post_id) and pagination
        returns posts after this cursor.

        Args:
            limit: Maximum posts to return.
            after_created_at: Cursor created_at value (posts before this).
            after_post_id: Cursor x_post_id value (for tie-breaking).

        Returns:
            Tuple of (posts list, has_more bool).
        """
        if after_created_at and after_post_id:
            # Get posts after the cursor
            rows = self._conn.execute(
                """
                SELECT * FROM posts
                WHERE (created_at < ?)
                   OR (created_at = ? AND x_post_id < ?)
                ORDER BY created_at DESC, x_post_id DESC
                LIMIT ?
                """,
                (after_created_at, after_created_at, after_post_id, limit + 1)
            ).fetchall()
        else:
            # First page - get most recent posts
            rows = self._conn.execute(
                """
                SELECT * FROM posts
                ORDER BY created_at DESC, x_post_id DESC
                LIMIT ?
                """,
                (limit + 1,)
            ).fetchall()

        posts = [self._row_to_dict(row) for row in rows]
        has_more = len(posts) > limit

        if has_more:
            posts = posts[:limit]

        return posts, has_more

    def get_paginated_with_embedded(
        self,
        limit: int = 20,
        after_created_at: Optional[str] = None,
        after_post_id: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Get posts with embedded post data for retweets/quotes.

        WEB-07, WEB-08: Include embedded post data in paginated results.
        Returns posts with 'embedded_post' key populated for retweets/quotes.

        Args:
            limit: Maximum posts to return.
            after_created_at: Cursor created_at value (posts before this).
            after_post_id: Cursor x_post_id value (for tie-breaking).

        Returns:
            Tuple of (posts list, has_more bool).
            Each post includes 'embedded_post' key (None for original posts).
        """
        if after_created_at and after_post_id:
            # Get posts after the cursor with embedded post data
            query = """
                SELECT p.*,
                       e.x_post_id as embedded_id,
                       e.created_at as embedded_created_at,
                       e.text as embedded_text,
                       e.author_id as embedded_author_id,
                       e.author_username as embedded_author_username,
                       e.author_display_name as embedded_author_display_name,
                       e.media_urls as embedded_media_urls,
                       e.link_urls as embedded_link_urls,
                       e.available as embedded_available
                FROM posts p
                LEFT JOIN embedded_posts e ON p.embedded_post_id = e.x_post_id
                WHERE (p.created_at < ?)
                   OR (p.created_at = ? AND p.x_post_id < ?)
                ORDER BY p.created_at DESC, p.x_post_id DESC
                LIMIT ?
            """
            rows = self._conn.execute(
                query,
                (after_created_at, after_created_at, after_post_id, limit + 1)
            ).fetchall()
        else:
            # First page - get most recent posts with embedded post data
            query = """
                SELECT p.*,
                       e.x_post_id as embedded_id,
                       e.created_at as embedded_created_at,
                       e.text as embedded_text,
                       e.author_id as embedded_author_id,
                       e.author_username as embedded_author_username,
                       e.author_display_name as embedded_author_display_name,
                       e.media_urls as embedded_media_urls,
                       e.link_urls as embedded_link_urls,
                       e.available as embedded_available
                FROM posts p
                LEFT JOIN embedded_posts e ON p.embedded_post_id = e.x_post_id
                ORDER BY p.created_at DESC, p.x_post_id DESC
                LIMIT ?
            """
            rows = self._conn.execute(query, (limit + 1,)).fetchall()

        posts = [self._row_to_dict_with_embedded(row) for row in rows]
        has_more = len(posts) > limit

        if has_more:
            posts = posts[:limit]

        return posts, has_more

    def _row_to_dict_with_embedded(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert row to dict with embedded post data.

        Handles LEFT JOIN result where embedded columns may be NULL
        for original posts (no embedded content).

        Args:
            row: SQLite Row object with post columns and embedded_ columns.

        Returns:
            Dict with post data and 'embedded_post' key.
            embedded_post is None for original posts.
        """
        post = self._row_to_dict(row)

        # Add embedded post if present (check for NULL, not truthy)
        # CRITICAL: Use 'is not None' check because embedded_id could be empty string
        if row['embedded_id'] is not None:
            post['embedded_post'] = {
                'x_post_id': row['embedded_id'],
                'created_at': row['embedded_created_at'],
                'text': row['embedded_text'],
                'author_id': row['embedded_author_id'],
                'author_username': row['embedded_author_username'],
                'author_display_name': row['embedded_author_display_name'],
                'media_urls': json.loads(row['embedded_media_urls']) if row['embedded_media_urls'] else [],
                'link_urls': json.loads(row['embedded_link_urls']) if row['embedded_link_urls'] else [],
                'available': bool(row['embedded_available']),
            }
        else:
            post['embedded_post'] = None

        return post