"""CLI entry point for x-bookmarked-posts.

Provides commands for:
- auth: Authenticate with X API using OAuth 2.0 PKCE (AUTH-01, AUTH-02, AUTH-03)
- init: Initialize the SQLite database (STOR-01, STOR-02)

Usage:
    xbm auth     # Authenticate with X
    xbm init     # Initialize database
    xbm --help   # Show all commands
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Union

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..auth import ensure_authenticated, AuthError
from ..db import init_database
from ..config import Settings

# Create Typer application with Rich markup support
app = typer.Typer(
    name="xbm",
    help="X Bookmarked Posts Organizer - CLI for managing X bookmarks",
    rich_markup_mode="rich",
)

# Rich console for styled output
console = Console()


@app.command()
def auth() -> None:
    """Authenticate with X API using OAuth 2.0 PKCE flow.

    AUTH-01: User can authenticate with X via OAuth 2.0 PKCE flow.
    AUTH-02: Application stores and refreshes access tokens securely.
    AUTH-03: Application handles token expiration gracefully.

    This command will:
    1. Check for existing tokens in data/tokens.json
    2. If no tokens, initiate OAuth 2.0 PKCE flow:
       - Print authorization URL
       - Start callback server on localhost:8080
       - Exchange authorization code for tokens
       - Save tokens to data/tokens.json
    3. Return success message

    Raises:
        SystemExit: On authentication failure (exit code 1).
    """
    try:
        # Load settings (validates X_CLIENT_ID and X_CLIENT_SECRET exist)
        settings = Settings()

        # Ensure authenticated (runs OAuth flow if needed)
        auth_data = ensure_authenticated(
            client_id=settings.client_id,
            client_secret=settings.client_secret_value,
            token_path=settings.token_path,
        )

        # Success message with Rich formatting
        console.print(Panel(
            Text.assemble(
                ("Successfully authenticated!", "bold green"),
                "\n\n",
                ("Client ID: ", "dim"),
                (auth_data.client_id, "cyan"),
            ),
            title="[bold]X API Authentication[/bold]",
            border_style="green",
        ))

    except AuthError as e:
        # AUTH-03: Clear error message
        console.print(Panel(
            Text.assemble(
                ("Authentication failed\n", "bold red"),
                (str(e), "red"),
                "\n\n",
                ("Troubleshooting:", "bold yellow"),
                "\n- Verify X_CLIENT_ID and X_CLIENT_SECRET in .env file",
                "\n- Check that app is configured in X Developer Portal",
                "\n- Ensure redirect URI is http://127.0.0.1:8080/callback",
            ),
            title="[bold red]Authentication Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)

    except Exception as e:
        # Unexpected error
        console.print(Panel(
            Text.assemble(
                ("Unexpected error\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def init(
    db_path: Path = typer.Option(
        None,
        "--db",
        "-d",
        help="Path to database file (default: data/bookmarks.db)",
    ),
) -> None:
    """Initialize the SQLite database with required tables.

    STOR-01: Application stores posts in SQLite database with WAL mode enabled.
    STOR-02: Application enables foreign key constraints on database connections.

    This command will:
    1. Create data/ directory if it doesn't exist
    2. Create SQLite database with WAL mode
    3. Create users and tokens tables
    4. Create indexes for performance

    Args:
        db_path: Optional path to database file. Uses Settings.database_path if not provided.

    Raises:
        SystemExit: On initialization failure (exit code 1).
    """
    try:
        # Determine database path
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                # Settings not configured, use default
                db_path = Path("data/bookmarks.db")

        # Initialize database
        conn = init_database(db_path)
        conn.close()

        # Success message with Rich formatting
        console.print(Panel(
            Text.assemble(
                ("Database initialized successfully!", "bold green"),
                "\n\n",
                ("Location: ", "dim"),
                (str(db_path), "cyan"),
                "\n",
                ("Tables: ", "dim"),
                ("users, tokens", "cyan"),
            ),
            title="[bold]Database Initialization[/bold]",
            border_style="green",
        ))

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Database initialization failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Initialization Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def verify() -> None:
    """Verify current authentication status.

    Checks if stored tokens are valid by calling X API GET /2/users/me.

    Raises:
        SystemExit: On verification failure (exit code 1).
    """
    try:
        settings = Settings()
        auth_data = ensure_authenticated(
            client_id=settings.client_id,
            client_secret=settings.client_secret_value,
            token_path=settings.token_path,
        )

        # Import verify_credentials
        from ..auth.oauth import verify_credentials

        user_data = verify_credentials(auth_data.access_token)

        # Success message
        username = getattr(user_data, 'username', 'Unknown')
        console.print(Panel(
            Text.assemble(
                ("Authentication verified!\n", "bold green"),
                "\n",
                ("Username: ", "dim"),
                (f"@{username}", "cyan"),
            ),
            title="[bold]X API Verification[/bold]",
            border_style="green",
        ))

    except AuthError as e:
        console.print(Panel(
            Text.assemble(
                ("Verification failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Verification Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()