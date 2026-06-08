"""Home page routes.

WEB-04: User can browse posts with cursor-based pagination.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Render the home page with recent posts.

    Args:
        request: FastAPI request object.

    Returns:
        HTML response with home page.
    """
    templates = request.app.state.templates

    # Check if user is authenticated
    has_tokens = getattr(request.app.state, "has_tokens", False)

    # For now, render a placeholder home page
    # Full post browsing will be implemented in Wave 3
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "has_tokens": has_tokens,
            "posts": [],
        },
    )