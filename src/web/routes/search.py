"""Search routes for full-text search and filtering.

WEB-05: User can search posts by text content (FTS5).
WEB-06: User can filter posts by topic, author, and date range.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..auth import UserContext, get_current_user
from ...db import init_database
from ...services.search import SearchService
from ...repositories.posts import PostsRepository
from ...repositories.topics import TopicsRepository

router = APIRouter(tags=["search"])


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = Query(None, description="Search query"),
    topic: str = Query(None, description="Filter by topic name"),
    author: str = Query(None, description="Filter by author username"),
    from_date: str = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """Render search page with results.

    Args:
        request: FastAPI request object.
        q: Full-text search query.
        topic: Filter by topic name.
        author: Filter by author username.
        from_date: Filter from date.
        to_date: Filter to date.
        limit: Maximum results.

    Returns:
        HTML response with search results.
    """
    templates = request.app.state.templates
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        search_service = SearchService(conn)
        topics_repo = TopicsRepository(conn)

        results = []
        if q:
            # Use existing FTS5 search service
            results = search_service.search(q, author=author, limit=limit)

        # Get all topics for filter dropdown
        topics = topics_repo.list_topics()

        conn.close()

        return templates.TemplateResponse(
            request,
            "search.html",
            {
                "query": q or "",
                "results": results,
                "topics": topics,
                "selected_topic": topic,
                "selected_author": author,
                "from_date": from_date,
                "to_date": to_date,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error": str(e)},
        )


@router.get("/api/search")
async def api_search(
    q: str = Query(None, description="Search query"),
    topic: str = Query(None, description="Filter by topic name"),
    author: str = Query(None, description="Filter by author username"),
    from_date: str = Query(None, description="Filter from date"),
    to_date: str = Query(None, description="Filter to date"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """JSON endpoint for search (HTMX).

    Args:
        q: Full-text search query.
        topic: Filter by topic name.
        author: Filter by author username.
        from_date: Filter from date.
        to_date: Filter to date.
        limit: Maximum results.

    Returns:
        JSON with search results.
    """
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        search_service = SearchService(conn)

        results = []
        if q:
            results = search_service.search(q, author=author, limit=limit)

        conn.close()

        return JSONResponse({
            "query": q,
            "results": [
                {
                    "x_post_id": r.x_post_id,
                    "author_username": r.author_username,
                    "snippet": r.snippet,
                    "created_at": r.created_at,
                }
                for r in results
            ],
            "count": len(results),
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/topics")
async def api_topics():
    """JSON endpoint for all topics (filter dropdown).

    Returns:
        JSON list of topics.
    """
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        topics_repo = TopicsRepository(conn)
        topics = topics_repo.list_topics()
        conn.close()

        return JSONResponse({
            "topics": [
                {"id": t["id"], "name": t["name"]}
                for t in topics
            ]
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/authors")
async def api_authors(
    q: str = Query(None, description="Author name prefix"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
):
    """JSON endpoint for author autocomplete.

    Args:
        q: Author name prefix to search.
        limit: Maximum results.

    Returns:
        JSON list of matching author usernames.
    """
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        posts_repo = PostsRepository(conn)

        # Query distinct authors matching prefix
        if q:
            rows = conn.execute(
                """
                SELECT DISTINCT author_username
                FROM posts
                WHERE author_username LIKE ?
                ORDER BY author_username
                LIMIT ?
                """,
                (f"{q}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT author_username
                FROM posts
                ORDER BY author_username
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        conn.close()

        return JSONResponse({
            "authors": [row["author_username"] for row in rows]
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Import Depends at end to avoid circular imports
from fastapi import Depends  # noqa: E402