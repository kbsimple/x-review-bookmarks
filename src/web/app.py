"""FastAPI application factory for the web interface.

WEB-01: User can access application via web browser at localhost.
WEB-02: Web app serves posts over HTTPS (required for Google Cast).
"""

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import home, auth, browse, search, cast


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup: check for tokens
    from ..auth.oauth import load_tokens

    tokens = load_tokens()
    app.state.has_tokens = tokens is not None

    yield

    # Shutdown: cleanup if needed
    pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="X Bookmarked Posts",
        description="Web interface for browsing and searching bookmarked posts",
        version="1.1.0",
        lifespan=lifespan,
    )

    # Templates directory
    templates_dir = Path(__file__).parent / "templates"
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # Static files
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routes
    app.include_router(home.router)
    app.include_router(auth.router)
    app.include_router(browse.router)
    app.include_router(search.router)
    app.include_router(cast.router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {"status": "healthy"}

    return app