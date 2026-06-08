"""Browse routes for post pagination.

WEB-04: User can browse posts with cursor-based pagination.
WEB-DB-01: Database connections managed via FastAPI dependency.
"""

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3

from ..pagination import Cursor
from ..database import get_db
from ...repositories.posts import PostsRepository

router = APIRouter(tags=["browse"])


@router.get("/browse", response_class=HTMLResponse)
async def browse_page(
    request: Request,
    cursor: str = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Posts per page"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render browse page with paginated posts.

    Args:
        request: FastAPI request object.
        cursor: Pagination cursor (optional, for next page).
        limit: Number of posts per page.
        conn: Database connection (injected via dependency).

    Returns:
        HTML response with browse page.
    """
    templates = request.app.state.templates

    try:
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
    conn: sqlite3.Connection = Depends(get_db),
):
    """JSON endpoint for paginated posts (HTMX infinite scroll).

    Args:
        cursor: Pagination cursor (optional).
        limit: Number of posts per page.
        conn: Database connection (injected via dependency).

    Returns:
        JSON with posts and pagination metadata.
    """
    try:
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

        return JSONResponse({
            "posts": posts,
            "next_cursor": next_cursor,
            "has_more": has_more,
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/posts/html", response_class=HTMLResponse)
async def api_posts_html(
    request: Request,
    cursor: str = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Posts per page"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Return HTML snippets for HTMX infinite scroll.

    WEB-07, WEB-08, WEB-09, WEB-10: Render post cards with embedded content.

    This endpoint returns HTML snippets that HTMX can directly append to
    the posts container. Uses the same _post_card.html macro as the browse
    page for consistent rendering.

    Args:
        request: FastAPI request object.
        cursor: Pagination cursor (optional, for next page).
        limit: Number of posts per page.
        conn: Database connection (injected via dependency).

    Returns:
        HTML response with post cards to append to container.
        X-Has-More header indicates if more posts exist.
    """
    templates = request.app.state.templates

    try:
        repo = PostsRepository(conn)

        # Decode cursor if provided
        after_created_at = None
        after_post_id = None
        if cursor:
            decoded = Cursor.decode(cursor)
            if decoded:
                after_created_at = decoded.created_at
                after_post_id = decoded.x_post_id

        # Get paginated posts with embedded post data
        posts, has_more = repo.get_paginated_with_embedded(
            limit=limit,
            after_created_at=after_created_at,
            after_post_id=after_post_id,
        )

        # Generate next cursor for Load More button
        next_cursor = None
        if has_more and posts:
            last_post = posts[-1]
            next_cursor = Cursor(
                created_at=last_post["created_at"],
                x_post_id=last_post["x_post_id"],
            ).encode()

        # Render HTML snippet using post card template
        return templates.TemplateResponse(
            request,
            "components/_post_snippets.html",
            {
                "posts": posts,
                "has_more": has_more,
                "next_cursor": next_cursor,
            },
            headers={"X-Has-More": str(has_more).lower()}
        )

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error": str(e)},
            status_code=500
        )