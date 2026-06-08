"""Authentication routes for the web interface.

WEB-03: Shared authentication with CLI.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse

from ..auth import UserContext, get_current_user

router = APIRouter(tags=["auth"])


@router.get("/api/auth/status")
async def auth_status(user: UserContext = Depends(get_current_user)) -> JSONResponse:
    """Return authentication status as JSON.

    Returns:
        JSON with authenticated boolean.
    """
    return JSONResponse({
        "authenticated": user.authenticated,
        "username": user.username if user.authenticated else None,
    })


@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login instructions for unauthenticated users.

    Returns:
        HTML page with authentication instructions.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {},
    )