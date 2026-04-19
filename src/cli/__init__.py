"""CLI module for x-bookmarked-posts.

Provides Typer application with commands for:
- auth: Authenticate with X API using OAuth 2.0 PKCE
- init: Initialize the database

Usage:
    from src.cli import app

    # Or run directly:
    python -m src.cli.main auth
"""

from .main import app

__all__ = ["app"]