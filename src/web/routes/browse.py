"""Browse routes for post pagination.

WEB-04: User can browse posts with cursor-based pagination.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import sqlite3

from ..pagination import Cursor, Page
from ..auth import UserContext, get_current_user
from ...db import init_database
from ...repositories.posts import PostsRepository

router = APIRouter(tags=["browse"])


@router.get("/browse", response_class=HTMLResponse)
async def browse_page(
    request: Request,
    cursor: str = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Posts per page"),
):
    """Render browse page with paginated posts.

    Args:
        request: FastAPI request object.
        cursor: Pagination cursor (optional, for next page).
        limit: Number of posts per page.

    Returns:
        HTML response with browse page.
    """
    templates = request.app.state.templates
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        repo = PostsRepository(conn)

        # Decode cursor if provided
        after_created_at = None
        after_post_id = None
        if cursor:
            decoded = Cursor.decode(cursor)
            if decoded:
                after_created_at = decoded.created_at
                after_post_id = decoded.x_post_id

        # Get paginated posts with embedded post data for retweets/quotes
        # WEB-07, WEB-08: Include embedded post data for template rendering
        posts, has_more = repo.get_paginated_with_embedded(
            limit=limit,
            after_created_at=after_created_at,
            after_post_id=after_post_id,
        )

        # Generate next cursor if there are more posts
        next_cursor = None
        if has_more and posts:
            last_post = posts[-1]
            next_cursor = Cursor(
                created_at=last_post["created_at"],
                x_post_id=last_post["x_post_id"],
            ).encode()

        conn.close()

        return templates.TemplateResponse(
            request,
            "browse.html",
            {
                "posts": posts,
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error": str(e)},
        )


@router.get("/api/posts")
async def api_posts(
    cursor: str = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Posts per page"),
):
    """JSON endpoint for paginated posts (HTMX infinite scroll).

    Args:
        cursor: Pagination cursor (optional).
        limit: Number of posts per page.

    Returns:
        JSON with posts and pagination metadata.
    """
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        repo = PostsRepository(conn)

        # Decode cursor if provided
        after_created_at = None
        after_post_id = None
        if cursor:
            decoded = Cursor.decode(cursor)
            if decoded:
                after_created_at = decoded.created_at
                after_post_id = decoded.x_post_id

        # Get paginated posts with embedded post data for retweets/quotes
        # WEB-07, WEB-08: Include embedded post data in JSON response
        posts, has_more = repo.get_paginated_with_embedded(
            limit=limit,
            after_created_at=after_created_at,
            after_post_id=after_post_id,
        )

        # Generate next cursor
        next_cursor = None
        if has_more and posts:
            last_post = posts[-1]
            next_cursor = Cursor(
                created_at=last_post["created_at"],
                x_post_id=last_post["x_post_id"],
            ).encode()

        conn.close()

        return JSONResponse({
            "posts": posts,
            "next_cursor": next_cursor,
            "has_more": has_more,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Import Depends at end to avoid circular imports
from fastapi import Depends  # noqa: E402