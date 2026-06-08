"""Web application module for X Bookmarked Posts.

This module provides a FastAPI web interface for browsing and searching
bookmarked posts. It shares authentication with the CLI via data/tokens.json.
"""

from .app import create_app

__all__ = ["create_app"]