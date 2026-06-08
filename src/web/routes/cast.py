"""Cast receiver routes.

RCVR-01: Custom Web Receiver displays post text and images on TV.
RCVR-02: Receiver handles post content loading from web app.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["cast"])


@router.get("/receiver", response_class=HTMLResponse)
async def receiver_page(request: Request):
    """Serve the Cast receiver page.

    This is the page that runs on the Chromecast/TV device
    and displays post content sent from the sender (web app).

    Returns:
        HTML receiver page.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "receiver.html",
        {},
    )


@router.get("/api/posts/{post_id}")
async def api_get_post(post_id: str):
    """Get a single post by ID for casting.

    CAST-06, CAST-07, CAST-08: Returns embedded_post data for retweets/quotes.
    Used by cast.js loadPost() to fetch post data for TV display.

    Args:
        post_id: The X post ID.

    Returns:
        JSON with post data including embedded_post field for retweets/quotes.
    """
    from pathlib import Path
    from ...db import init_database
    from ...repositories.posts import PostsRepository
    from ...repositories.topics import TopicsRepository

    db_path = Path("data/bookmarks.db")
    conn = init_database(db_path)

    try:
        posts_repo = PostsRepository(conn)
        topics_repo = TopicsRepository(conn)

        # Get post with embedded post data for retweets/quotes
        post = posts_repo.get_by_id_with_embedded(post_id)
        if not post:
            return {"error": "Post not found"}, 404

        # Get topics for the post
        topics = topics_repo.get_post_topics(post_id)
        post["topics"] = topics

        return post

    finally:
        conn.close()