"""CLI entry point for x-bookmarked-posts.

Provides commands for:
- auth: Authenticate with X API using OAuth 2.0 PKCE (AUTH-01, AUTH-02, AUTH-03)
- init: Initialize the SQLite database (STOR-01, STOR-02)
- sync: Sync bookmarks from X API to local database (CLI-01, CLI-05)

Usage:
    xbm auth     # Authenticate with X
    xbm init     # Initialize database
    xbm sync     # Sync bookmarks
    xbm --help   # Show all commands
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Union

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

from ..auth import AuthError, ensure_authenticated
from ..config import Settings
from ..db import init_database

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


@app.command()
def sync(
    db_path: Optional[Path] = typer.Option(
        None,
        "--db",
        "-d",
        help="Path to database file (default: data/bookmarks.db)",
    ),
) -> None:
    """Sync bookmarks from X API to local database.

    CLI-01: User can trigger bookmark sync via CLI command.
    CLI-05: Rich output with progress bar and summary.

    This command will:
    1. Authenticate with X API (runs OAuth flow if needed)
    2. Fetch bookmarks from X API with rate limit handling
    3. Store bookmarks in SQLite database
    4. Display progress bar during sync
    5. Show summary table after completion

    Args:
        db_path: Optional path to database file.

    Raises:
        SystemExit: On sync failure (exit code 1).
    """
    try:
        # Load settings and authenticate
        settings = Settings()
        auth_data = ensure_authenticated(
            client_id=settings.client_id,
            client_secret=settings.client_secret_value,
            token_path=settings.token_path,
        )

        # Determine database path
        if db_path is None:
            db_path = settings.database_path

        # Initialize database if needed
        conn = init_database(db_path)

        # Prepare progress tracking
        warnings_list: list[str] = []

        def on_rate_limit(wait_seconds: float) -> None:
            """Handle rate limit wait."""
            console.print(
                f"[yellow]Rate limit approaching. Waiting {wait_seconds:.0f}s...[/yellow]"
            )

        def on_warning(message: str) -> None:
            """Handle warnings."""
            warnings_list.append(message)

        # D-04: Progress bar during sync
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching bookmarks...", total=None)

            def on_progress(count: int) -> None:
                """Update progress display."""
                progress.update(task, description=f"Fetched {count} bookmarks")

            # Create sync service
            from ..services.sync import SyncService

            sync_service = SyncService(
                access_token=auth_data.access_token,
                conn=conn,
                on_rate_limit=on_rate_limit,
                on_warning=on_warning,
                on_progress=on_progress,
            )

            # Run sync
            result = sync_service.sync()

            # Update progress to complete
            progress.update(task, description=f"Complete! {result.total_fetched} bookmarks synced")

        # D-04: Summary table after sync
        summary_table = Table(title="Sync Summary", show_header=True, header_style="bold cyan")
        summary_table.add_column("Metric", style="dim")
        summary_table.add_column("Count", justify="right")

        summary_table.add_row("Total Fetched", str(result.total_fetched))
        summary_table.add_row("New", str(result.new_count))
        summary_table.add_row("Updated", str(result.updated_count))
        if result.error_count > 0:
            summary_table.add_row("Errors", f"[red]{result.error_count}[/red]")
        if result.rate_limit_waits > 0:
            summary_table.add_row("Rate Limit Waits", str(result.rate_limit_waits))

        console.print()
        console.print(summary_table)

        # Show warnings if any (from callback or from result)
        all_warnings = warnings_list + (result.warnings or [])
        if all_warnings:
            console.print()
            for warning in all_warnings:
                console.print(f"[yellow]Warning: {warning}[/yellow]")

        # D-04: Show sample of newly fetched posts
        if result.new_count > 0:
            console.print()
            console.print("[bold]Recent bookmarks:[/bold]")

            # Get recent posts
            from ..repositories import PostsRepository

            posts_repo = PostsRepository(conn)
            recent = posts_repo.get_all(limit=5)

            for post in recent:
                author = post.get('author_username', 'unknown')
                text = post.get('text', '')
                preview = text[:80] if text else ''
                console.print(f"  @{author}: {preview}...")

        # Close connection
        conn.close()

        # Success message
        console.print()
        console.print("[green]Sync complete![/green]")

    except AuthError as e:
        console.print(Panel(
            Text.assemble(
                ("Sync failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Authentication Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Sync failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (supports phrases, prefixes, boolean)"),
    author: Optional[str] = typer.Option(None, "--author", "-a", help="Filter by author username or display name"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results to return"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Path to database file"),
) -> None:
    """Search stored posts by content and author.

    SRCH-01: User can search within stored post content (full-text search).
    SRCH-02: User can search by author name or username.
    SRCH-03: Search results display relevant post content with context.
    CLI-03: User can search stored posts via CLI command.

    Examples:
        xbm search python
        xbm search "machine learning" --author "user123"
        xbm search python* --limit 50
    """
    try:
        # Get database connection
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)

        # Create search service
        from ..services.search import SearchService
        from ..repositories import PostsRepository

        repo = PostsRepository(conn)
        search_service = SearchService(conn)

        # Perform search
        results = search_service.search(query, author=author, limit=limit)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            conn.close()
            return

        # Build results table
        table = Table(title=f"Search Results for '{query}'" + (f" by @{author}" if author else ""))
        table.add_column("#", style="dim", width=4)
        table.add_column("Author", style="cyan")
        table.add_column("Snippet", style="white")
        table.add_column("Date", style="dim")

        for i, result in enumerate(results, 1):
            # Truncate snippet to 80 chars
            snippet = result.snippet[:80] + "..." if len(result.snippet) > 80 else result.snippet
            # Remove [match] markers for cleaner display (or style them)
            snippet = snippet.replace("[match]", "").replace("[/match]", "")

            table.add_row(
                str(i),
                f"@{result.author_username}",
                snippet,
                result.created_at[:10] if result.created_at else ""
            )

        console.print(table)
        console.print(f"[dim]Showing {len(results)} results[/dim]")

        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Search failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def note(
    post_id: str = typer.Argument(..., help="X post ID"),
    text: Optional[str] = typer.Argument(None, help="Note text (omit to show, use --clear to remove)"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Remove note from post"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Path to database file"),
) -> None:
    """Add, update, or remove a note on a post.

    NOTE-01: User can add personal notes to bookmarked posts.
    NOTE-02: Notes are displayed when post is resurfaced for review (Phase 5).

    Examples:
        xbm note 1234567890 "Remember to check this article"
        xbm note 1234567890                    # Show current note
        xbm note 1234567890 --clear            # Remove note
    """
    try:
        # Get database connection
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..repositories import PostsRepository

        repo = PostsRepository(conn)

        # Check if post exists
        post = repo.get_by_id(post_id)
        if not post:
            console.print(f"[red]Post not found: {post_id}[/red]")
            raise typer.Exit(1)

        if clear:
            # Remove note
            repo.update_note(post_id, None)
            console.print(f"[green]Note removed from post {post_id}[/green]")
        elif text is None:
            # Show existing note
            current_note = post.get('note')
            if current_note:
                console.print(Panel(
                    current_note,
                    title=f"[bold]Note for post {post_id}[/bold]",
                    border_style="cyan"
                ))
            else:
                console.print(f"[yellow]No note for post {post_id}[/yellow]")
                console.print(f"[dim]Add a note with: xbm note {post_id} \"your note\"[/dim]")
        else:
            # Add/update note
            repo.update_note(post_id, text)
            console.print(f"[green]Note added to post {post_id}[/green]")

        conn.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Note operation failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def export(
    format: str = typer.Option("json", "--format", "-f", help="Export format: json or csv"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Path to database file"),
) -> None:
    """Export stored posts to JSON or CSV.

    IMEX-01: User can export stored posts to JSON format.
    IMEX-02: User can export stored posts to CSV format.

    JSON format includes: version, exported_at, source, post_count, posts array.
    CSV format includes: x_post_id, text, author_username, author_display_name, created_at, note.

    Examples:
        xbm export --output bookmarks.json
        xbm export --format csv --output bookmarks.csv
        xbm export  # Prints to stdout with default JSON format
    """
    try:
        # Validate format
        if format not in ("json", "csv"):
            console.print(f"[red]Invalid format: {format}. Use 'json' or 'csv'.[/red]")
            raise typer.Exit(1)

        # Get database connection
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)

        # Determine output path
        if output is None:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output = Path(f"bookmarks_{timestamp}.{format}")

        # Create export service
        from ..repositories import PostsRepository
        from ..services.export import ExportService

        repo = PostsRepository(conn)
        export_service = ExportService(repo)

        # Perform export
        if format == "json":
            result = export_service.export_json(output)
        else:
            result = export_service.export_csv(output)

        # Success message
        console.print(Panel(
            Text.assemble(
                (f"Exported {result.post_count} posts\n", "bold green"),
                ("Format: ", "dim"),
                (f"{format.upper()}\n", "cyan"),
                ("Output: ", "dim"),
                (str(result.path), "cyan"),
            ),
            title="[bold]Export Complete[/bold]",
            border_style="green",
        ))

        conn.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Export failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()