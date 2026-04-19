"""Package entry point for x-bookmarked-posts.

Allows running the CLI via:
    python -m src

This is equivalent to:
    xbm auth
    xbm init
"""

from src.cli.main import app

if __name__ == "__main__":
    app()