"""SearchService for full-text search using SQLite FTS5.

SRCH-01: Full-text search within stored post content.
SRCH-02: Search by author name or username.
SRCH-03: Search results with context display (snippet highlighting).

Usage:
    from src.services.search import SearchService
    from src.db import get_connection

    conn = get_connection()
    search = SearchService(conn)
    results = search.search("python")
    results = search.search("python", author="guido")
    results = search.search_by_author("pythonista")
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """Result from a search query.

    Attributes:
        x_post_id: The X post ID.
        author_username: Author's username (@handle).
        author_display_name: Author's display name.
        created_at: Post creation timestamp.
        snippet: Text snippet with context around match.
        rank: bm25 relevance score (lower is better).
    """
    x_post_id: str
    author_username: str
    author_display_name: Optional[str]
    created_at: str
    snippet: str
    rank: float


class SearchService:
    """Full-text search service using SQLite FTS5.

    Provides:
    - Content search across text, author_username, author_display_name
    - bm25 relevance ranking
    - Snippet highlighting with context
    - Author-specific search
    """

    # FTS5 special characters that need escaping
    FTS5_SPECIAL_CHARS = ['(', ')', '*', '-', "'", '"']

    def __init__(self, conn: sqlite3.Connection):
        """Initialize search service with database connection.

        Args:
            conn: SQLite connection with row_factory set.
        """
        self._conn = conn

    def search(
        self,
        query: str,
        author: Optional[str] = None,
        limit: int = 20,
        highlight_markers: tuple[str, str] = ('...', '...')
    ) -> list[SearchResult]:
        """Search posts by content and optionally filter by author.

        Args:
            query: FTS5 search query (supports phrases, prefixes, boolean).
            author: Optional author filter (matches username or display_name).
            limit: Maximum results to return.
            highlight_markers: Tuple of (left, right) markers for highlighting.
                              Default is ('...', '...') for snippet ellipsis.

        Returns:
            List of SearchResult ordered by relevance (bm25).
        """
        # Handle empty/whitespace queries
        if not query or not query.strip():
            return []

        # Build FTS5 query
        fts_query = self._build_fts_query(query, author)

        # Execute search with bm25 ranking and snippet
        # FTS5 snippet(table, column, start_marker, end_marker, ellipsis, num_tokens)
        cursor = self._conn.execute(
            """
            SELECT
                p.x_post_id,
                p.author_username,
                p.author_display_name,
                p.created_at,
                snippet(posts_fts, 0, ?, ?, '...', 10) as snippet,
                bm25(posts_fts) as rank
            FROM posts_fts
            JOIN posts p ON p.rowid = posts_fts.rowid
            WHERE posts_fts MATCH ?
            ORDER BY bm25(posts_fts)
            LIMIT ?
            """,
            (highlight_markers[0], highlight_markers[1], fts_query, limit)
        )

        results = []
        for row in cursor.fetchall():
            results.append(SearchResult(
                x_post_id=row['x_post_id'],
                author_username=row['author_username'],
                author_display_name=row['author_display_name'],
                created_at=row['created_at'],
                snippet=row['snippet'],
                rank=row['rank']
            ))

        return results

    def search_by_author(
        self,
        author: str,
        limit: int = 20,
        highlight_markers: tuple[str, str] = ('...', '...')
    ) -> list[SearchResult]:
        """Search posts by author name or username.

        Searches both author_username and author_display_name columns.

        Args:
            author: Author name or username to search for.
            limit: Maximum results to return.
            highlight_markers: Tuple of (left, right) markers for highlighting.

        Returns:
            List of SearchResult ordered by relevance.
        """
        if not author or not author.strip():
            return []

        # Column-specific search for author fields
        fts_query = f"{{author_username author_display_name}} : {self._sanitize_query(author)}"

        cursor = self._conn.execute(
            """
            SELECT
                p.x_post_id,
                p.author_username,
                p.author_display_name,
                p.created_at,
                snippet(posts_fts, 0, ?, ?, '...', 10) as snippet,
                bm25(posts_fts) as rank
            FROM posts_fts
            JOIN posts p ON p.rowid = posts_fts.rowid
            WHERE posts_fts MATCH ?
            ORDER BY bm25(posts_fts)
            LIMIT ?
            """,
            (highlight_markers[0], highlight_markers[1], fts_query, limit)
        )

        results = []
        for row in cursor.fetchall():
            results.append(SearchResult(
                x_post_id=row['x_post_id'],
                author_username=row['author_username'],
                author_display_name=row['author_display_name'],
                created_at=row['created_at'],
                snippet=row['snippet'],
                rank=row['rank']
            ))

        return results

    def search_combined(
        self,
        query: str,
        author: str,
        limit: int = 20,
        highlight_markers: tuple[str, str] = ('...', '...')
    ) -> list[SearchResult]:
        """Search both text content AND author fields.

        Uses AND operator: text matches AND author matches.

        Args:
            query: Text search query.
            author: Author name or username.
            limit: Maximum results to return.
            highlight_markers: Tuple of (left, right) markers for highlighting.

        Returns:
            List of SearchResult matching both text and author.
        """
        if not query or not query.strip() or not author or not author.strip():
            return []

        # Text search AND author search
        text_query = self._sanitize_query(query)
        author_query = f"{{author_username author_display_name}} : {self._sanitize_query(author)}"
        fts_query = f"({text_query}) AND ({author_query})"

        cursor = self._conn.execute(
            """
            SELECT
                p.x_post_id,
                p.author_username,
                p.author_display_name,
                p.created_at,
                snippet(posts_fts, 0, ?, ?, '...', 10) as snippet,
                bm25(posts_fts) as rank
            FROM posts_fts
            JOIN posts p ON p.rowid = posts_fts.rowid
            WHERE posts_fts MATCH ?
            ORDER BY bm25(posts_fts)
            LIMIT ?
            """,
            (highlight_markers[0], highlight_markers[1], fts_query, limit)
        )

        results = []
        for row in cursor.fetchall():
            results.append(SearchResult(
                x_post_id=row['x_post_id'],
                author_username=row['author_username'],
                author_display_name=row['author_display_name'],
                created_at=row['created_at'],
                snippet=row['snippet'],
                rank=row['rank']
            ))

        return results

    def _build_fts_query(self, query: str, author: Optional[str] = None) -> str:
        """Build FTS5 query with optional author filter.

        Args:
            query: User's search query.
            author: Optional author filter.

        Returns:
            FTS5 query string.
        """
        sanitized_query = self._sanitize_query(query)

        if author:
            # Combine text query with author filter
            author_filter = f"{{author_username author_display_name}} : {self._sanitize_query(author)}"
            return f"({sanitized_query}) AND ({author_filter})"

        return sanitized_query

    def _sanitize_query(self, query: str) -> str:
        """Sanitize query for FTS5 to prevent syntax errors.

        Removes/escapes FTS5 special characters while preserving
        phrase queries in quotes.

        Args:
            query: Raw user query.

        Returns:
            Sanitized FTS5-safe query.
        """
        if not query:
            return ""

        # If the query is already a quoted phrase, return it as-is
        if query.startswith('"') and query.endswith('"') and query.count('"') == 2:
            return query

        # Remove FTS5 special characters that could cause syntax errors
        # Keep quotes for phrase queries
        sanitized = query

        # Escape or remove problematic characters
        # FTS5 special chars: ( ) * - ' "

        # Remove parentheses (they're FTS5 syntax)
        sanitized = sanitized.replace('(', ' ').replace(')', ' ')

        # Handle asterisks - keep them for prefix search but ensure proper context
        # A lone * is problematic, *word is prefix search
        sanitized = re.sub(r'(?<!\w)\*(?!\w)', ' ', sanitized)  # Remove isolated *
        sanitized = re.sub(r'\*(?=\w)', '', sanitized)  # Remove * before word
        # Keep * after word for prefix search (word*)

        # Handle hyphens - they're FTS5 NOT operator
        # For hyphenated words like "test-case", treat as single term by quoting
        # Replace hyphens within words with spaces (treat as separate terms)
        if '-' in sanitized and '"' not in sanitized:
            # If hyphen appears between letters (e.g., "test-case"), replace with space
            # to search for both terms
            sanitized = re.sub(r'(\w)-(\w)', r'\1 \2', sanitized)

        # Clean up multiple spaces
        sanitized = ' '.join(sanitized.split())

        return sanitized if sanitized.strip() else ""