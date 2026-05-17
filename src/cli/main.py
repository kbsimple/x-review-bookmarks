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

# Suppress urllib3 OpenSSL warning on macOS (LibreSSL vs OpenSSL)
# Must be before imports that trigger the warning
import warnings
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

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
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of bookmarks to fetch (default: all)",
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
        limit: Maximum number of bookmarks to fetch. If None, fetches all.

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
            result = sync_service.sync(limit=limit)

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
def browse(
    order: str = typer.Option(
        "newest",
        "--order", "-o",
        help="Sort order: newest, oldest, or random",
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum posts to display"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Path to database file"),
) -> None:
    """Browse all bookmarked posts.

    Display full post content in the specified order for casual browsing.

    Examples:
        xbm browse                    # Newest first (default)
        xbm browse --order oldest     # Oldest first
        xbm browse --order random     # Random order
        xbm browse -o random -l 50    # 50 random posts
    """
    valid_orders = {"newest", "oldest", "random"}
    if order not in valid_orders:
        console.print(f"[red]Invalid order '{order}'. Must be one of: {', '.join(valid_orders)}[/red]")
        raise typer.Exit(1)

    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..repositories import PostsRepository
        from ..repositories.topics import TopicsRepository
        from .display import display_post, display_post_separator

        repo = PostsRepository(conn)
        topics_repo = TopicsRepository(conn)
        posts = repo.get_all_ordered(order=order, limit=limit)

        if not posts:
            console.print("[yellow]No posts found[/yellow]")
            conn.close()
            return

        # Show session header
        total = repo.count()
        console.print()
        console.print(f"[bold]Browsing {len(posts)} of {total} posts ({order})[/bold]")
        console.print()

        # Display each post
        for i, post in enumerate(posts, 1):
            post_topics = topics_repo.get_post_topics(post['x_post_id'])
            display_post(console, post, topics=post_topics)

            # Show separator between posts (except last)
            if i < len(posts):
                display_post_separator(console)

        console.print(f"[dim]Showing {len(posts)} of {total} posts[/dim]")

        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Failed to browse posts\n", "bold red"),
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


@app.command("import")
def import_cmd(
    file: Path = typer.Argument(..., help="Path to JSON export file"),
    update: bool = typer.Option(False, "--update", "-u", help="Update existing posts instead of skipping"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Path to database file"),
) -> None:
    """Import posts from JSON export file.

    IMEX-03: User can import posts from JSON export.

    Import validates:
    - File exists and is valid JSON
    - version field is "1.0"
    - source field is "xbm"

    By default, skips existing posts. Use --update to overwrite.

    Examples:
        xbm import bookmarks_2024-01-15.json
        xbm import bookmarks.json --update
    """
    try:
        # Validate file exists
        if not file.exists():
            console.print(f"[red]File not found: {file}[/red]")
            raise typer.Exit(1)

        # Get database connection
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)

        # Create import service
        from ..repositories import PostsRepository
        from ..services.export import ImportService

        repo = PostsRepository(conn)
        import_service = ImportService(repo)

        # Perform import
        conflict = "update" if update else "skip"
        result = import_service.import_json(file, conflict=conflict)

        # Build result message
        message_parts = [
            (f"Imported: {result.imported_count}\n", "green"),
            (f"Skipped: {result.skipped_count}\n", "yellow" if result.skipped_count > 0 else "dim"),
        ]
        if result.error_count > 0:
            message_parts.append((f"Errors: {result.error_count}\n", "red"))

        console.print(Panel(
            Text.assemble(*message_parts),
            title="[bold]Import Complete[/bold]",
            border_style="green" if result.error_count == 0 else "yellow",
        ))

        # Show errors if any
        if result.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for error in result.errors[:5]:  # Show first 5 errors
                console.print(f"  [red]• {error}[/red]")
            if len(result.errors) > 5:
                console.print(f"  [dim]... and {len(result.errors) - 5} more[/dim]")

        conn.close()

    except typer.Exit:
        raise
    except ValueError as e:
        console.print(Panel(
            Text.assemble(
                ("Import validation failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Import failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command("check-links")
def check_links(
    force: bool = typer.Option(False, "--force", "-f", help="Recheck all links, ignoring cache"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Path to database file"),
) -> None:
    """Check all links in stored posts and flag dead links.

    MAINT-01: Application detects and flags dead links in stored posts.
    MAINT-02: Application can filter dead links from review queue.

    Checks links concurrently (max 10 at a time) with timeout handling.
    Results cached for 30 days unless --force used.

    Examples:
        xbm check-links
        xbm check-links --force
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

        # Prepare progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Checking links...", total=None)

            def on_progress(completed: int, total: int) -> None:
                progress.update(task, completed=completed, total=total)

            # Create link checker service
            from ..repositories import PostsRepository
            from ..services.link_checker import LinkCheckerService

            repo = PostsRepository(conn)
            checker = LinkCheckerService(repo, on_progress=on_progress)

            # Run check
            result = checker.check_all_links_sync(force=force)

            progress.update(task, description=f"Checked {result.total_checked} links")

        # Show summary table
        table = Table(title="Link Check Summary", show_header=True, header_style="bold cyan")
        table.add_column("Status", style="dim")
        table.add_column("Count", justify="right")

        table.add_row("OK", str(result.ok_count))
        table.add_row("Dead", f"[red]{result.dead_count}[/red]" if result.dead_count > 0 else "0")
        table.add_row("Error", f"[yellow]{result.error_count}[/yellow]" if result.error_count > 0 else "0")
        table.add_row("Total", str(result.total_checked))

        console.print()
        console.print(table)

        # Show dead links if any
        if result.dead_count > 0:
            console.print("\n[bold red]Dead Links:[/bold red]")
            dead_links = [(pid, url) for pid, url, status in result.results if status.status == "dead"]
            for post_id, url in dead_links[:5]:  # Show first 5
                console.print(f"  [red]• {url}[/red] [dim](post: {post_id})[/dim]")
            if len(dead_links) > 5:
                console.print(f"  [dim]... and {len(dead_links) - 5} more[/dim]")

        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Link check failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command("tag")
def tag(
    post_id: Optional[str] = typer.Argument(None, help="X post ID (omit for --list)"),
    tag_name: Optional[str] = typer.Argument(None, help="Tag name to assign/remove"),
    remove: bool = typer.Option(False, "--remove", "-r", help="Remove tag from post"),
    list_tags: bool = typer.Option(False, "--list", "-l", help="List all tags"),
    show: bool = typer.Option(False, "--show", "-s", help="Show tags for post"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Manage tags for bookmarked posts.

    CLI-04: User can manage tags via CLI commands.

    Examples:
        xbm tag post_123 python           # Add 'python' tag to post
        xbm tag post_123 "machine learning"  # Tag with space
        xbm tag post_123 --remove python  # Remove tag
        xbm tag post_123 --show           # Show post's tags
        xbm tag --list                    # List all tags
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..repositories.tags import TagsRepository
        from ..repositories.posts import PostsRepository

        tags_repo = TagsRepository(conn)
        posts_repo = PostsRepository(conn)

        if list_tags:
            # List all tags
            tags = tags_repo.list_tags()
            if not tags:
                console.print("[yellow]No tags found[/yellow]")
                conn.close()
                return

            table = Table(title="Tags")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="cyan")
            table.add_column("Created", style="dim")

            for tag in tags:
                table.add_row(str(tag['id']), tag['name'], str(tag.get('created_at', ''))[:10])

            console.print(table)
            conn.close()
            return

        if post_id is None:
            console.print("[red]Error: post_id required unless using --list[/red]")
            raise typer.Exit(1)

        # Verify post exists
        post = posts_repo.get_by_id(post_id)
        if not post:
            console.print(f"[red]Post not found: {post_id}[/red]")
            raise typer.Exit(1)

        if show:
            # Show tags for post
            tags = tags_repo.get_post_tags(post_id)
            if not tags:
                console.print(f"[yellow]No tags for post {post_id}[/yellow]")
            else:
                console.print(f"[bold]Tags for post {post_id}:[/bold]")
                for tag in tags:
                    console.print(f"  - {tag['name']}")
            conn.close()
            return

        if tag_name is None:
            console.print("[red]Error: tag_name required unless using --show[/red]")
            raise typer.Exit(1)

        if remove:
            # Remove tag
            tag = tags_repo.get_tag_by_name(tag_name)
            if tag:
                tags_repo.remove_tag(post_id, tag['id'])
                console.print(f"[green]Removed tag '{tag_name}' from post {post_id}[/green]")
            else:
                console.print(f"[yellow]Tag '{tag_name}' not found[/yellow]")
        else:
            # Add tag
            tag_id = tags_repo.get_or_create_tag(tag_name)
            tags_repo.assign_tag(post_id, tag_id)
            console.print(f"[green]Added tag '{tag_name}' to post {post_id}[/green]")

        conn.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Tag operation failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command("topic")
def topic(
    action: Optional[str] = typer.Argument(None, help="Action: create, assign, delete, or topic_id for --show"),
    name_or_id: Optional[str] = typer.Argument(None, help="Topic name (for create) or post_id (for assign) or topic_id (for delete)"),
    topic_id: Optional[int] = typer.Argument(None, help="Topic ID for assignment"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Topic description"),
    list_topics: bool = typer.Option(False, "--list", "-l", help="List all topics"),
    show: bool = typer.Option(False, "--show", "-s", help="Show topics for post (action=post_id)"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Manage topic taxonomy.

    CLI-04: User can manage topics via CLI commands.

    Examples:
        xbm topic create "Programming" --desc "Software development"
        xbm topic --list
        xbm topic assign post_123 1        # Assign topic 1 to post
        xbm topic post_123 --show          # Show post's topics
        xbm topic delete 1                 # Delete topic 1
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..repositories.topics import TopicsRepository
        from ..repositories.posts import PostsRepository

        topics_repo = TopicsRepository(conn)
        posts_repo = PostsRepository(conn)

        if list_topics:
            # List all topics
            topics = topics_repo.list_topics()
            if not topics:
                console.print("[yellow]No topics found[/yellow]")
                conn.close()
                return

            table = Table(title="Topics")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Posts", style="dim")

            for topic in topics:
                posts = topics_repo.get_posts_by_topic(topic['id'])
                table.add_row(
                    str(topic['id']),
                    topic['name'],
                    topic.get('description', '')[:40] or '',
                    str(len(posts))
                )

            console.print(table)
            conn.close()
            return

        if action is None:
            console.print("[red]Error: action required (create, assign, delete, or post_id with --show)[/red]")
            console.print("[dim]Use 'xbm topic --help' for usage[/dim]")
            raise typer.Exit(1)

        if action == "create":
            # Create topic
            if name_or_id is None:
                console.print("[red]Error: topic name required for create[/red]")
                raise typer.Exit(1)

            try:
                topic_id_result = topics_repo.create_topic(name_or_id, description)
                console.print(f"[green]Created topic '{name_or_id}' (ID: {topic_id_result})[/green]")
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    console.print(f"[red]Topic '{name_or_id}' already exists[/red]")
                else:
                    raise
            conn.close()
            return

        if action == "assign":
            # Assign topic to post
            if name_or_id is None or topic_id is None:
                console.print("[red]Error: post_id and topic_id required for assign[/red]")
                raise typer.Exit(1)

            post_id = name_or_id

            # Verify post exists
            post = posts_repo.get_by_id(post_id)
            if not post:
                console.print(f"[red]Post not found: {post_id}[/red]")
                raise typer.Exit(1)

            # Verify topic exists
            topic_obj = topics_repo.get_topic_by_id(topic_id)
            if not topic_obj:
                console.print(f"[red]Topic not found: {topic_id}[/red]")
                raise typer.Exit(1)

            topics_repo.assign_topic_to_post(post_id, topic_id)
            console.print(f"[green]Assigned topic '{topic_obj['name']}' to post {post_id}[/green]")
            conn.close()
            return

        if action == "delete":
            # Delete topic
            if name_or_id is None:
                console.print("[red]Error: topic_id required for delete[/red]")
                raise typer.Exit(1)

            try:
                topic_id_to_delete = int(name_or_id)
            except ValueError:
                console.print(f"[red]Invalid topic_id: {name_or_id}[/red]")
                raise typer.Exit(1)

            topic_obj = topics_repo.get_topic_by_id(topic_id_to_delete)
            if not topic_obj:
                console.print(f"[red]Topic not found: {topic_id_to_delete}[/red]")
                raise typer.Exit(1)

            topics_repo.delete_topic(topic_id_to_delete)
            console.print(f"[green]Deleted topic '{topic_obj['name']}'[/green]")
            conn.close()
            return

        # Treat action as post_id for --show
        if show:
            post_id = action
            # Verify post exists
            post = posts_repo.get_by_id(post_id)
            if not post:
                console.print(f"[red]Post not found: {post_id}[/red]")
                raise typer.Exit(1)

            topics = topics_repo.get_post_topics(post_id)
            if not topics:
                console.print(f"[yellow]No topics for post {post_id}[/yellow]")
            else:
                console.print(f"[bold]Topics for post {post_id}:[/bold]")
                for topic_obj in topics:
                    source = topic_obj.get('source', 'user')
                    confidence = topic_obj.get('confidence')
                    conf_str = f" ({confidence:.2f})" if confidence else ""
                    console.print(f"  - {topic_obj['name']}{conf_str} [{source}]")
            conn.close()
            return

        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[dim]Use 'xbm topic --help' for usage[/dim]")
        raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Topic operation failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command("suggest-topics")
def suggest_topics(
    threshold: float = typer.Option(0.6, "--threshold", "-t", help="Minimum confidence threshold"),
    clear: bool = typer.Option(True, "--clear/--no-clear", help="Clear existing suggestions first"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Generate AI topic suggestions for unassigned posts.

    ORG-03: Application clusters posts into topics using hybrid approach.

    Analyzes posts without topic assignments and generates suggestions
    based on semantic similarity to existing topic centroids.

    Suggestions are stored as pending assignments for review.

    Examples:
        xbm suggest-topics
        xbm suggest-topics --threshold 0.7
        xbm suggest-topics --no-clear  # Keep existing suggestions
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)

        from ..services.topic_suggester import TopicSuggesterService

        # Create service with specified threshold
        service = TopicSuggesterService(
            conn,
            confidence_threshold=threshold
        )

        console.print("[bold]Generating topic suggestions...[/bold]")

        # Generate suggestions
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing posts...", total=None)

            summary = service.generate_all_suggestions(
                clear_existing=clear,
                show_progress=True
            )

            progress.update(task, description="Complete!")

        # Show summary
        table = Table(title="Suggestion Summary")
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Posts Processed", str(summary.total_posts_processed))
        table.add_row("Suggestions Generated", str(summary.total_suggestions))
        table.add_row("Posts with Suggestions", str(summary.posts_with_suggestions))

        console.print()
        console.print(table)

        if summary.suggestions_by_topic:
            console.print()
            console.print("[bold]Suggestions by Topic:[/bold]")
            for topic_name, count in sorted(summary.suggestions_by_topic.items(), key=lambda x: -x[1]):
                console.print(f"  {topic_name}: {count}")

        console.print()
        console.print("[dim]Use 'xbm review-topics' to review and approve suggestions[/dim]")

        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Suggestion generation failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command("review-topics")
def review_topics(
    approve: Optional[int] = typer.Option(None, "--approve", "-a", help="Approve suggestion by ID"),
    reject: Optional[int] = typer.Option(None, "--reject", "-r", help="Reject suggestion by ID"),
    approve_all: bool = typer.Option(False, "--approve-all", help="Approve all pending suggestions"),
    min_confidence: float = typer.Option(0.0, "--min-confidence", "-c", help="Min confidence for --approve-all"),
    post_id: Optional[str] = typer.Option(None, "--post", "-p", help="Filter by post ID"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Review and approve/reject AI topic suggestions.

    ORG-04: User can review and approve AI-suggested topic assignments.

    Examples:
        xbm review-topics                    # Show all pending suggestions
        xbm review-topics --post post_123    # Show suggestions for a post
        xbm review-topics --approve 1        # Approve suggestion #1
        xbm review-topics --reject 1         # Reject suggestion #1
        xbm review-topics --approve-all      # Approve all suggestions
        xbm review-topics --approve-all --min-confidence 0.8
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)

        from ..services.topic_suggester import TopicSuggesterService
        from ..repositories.topics import TopicsRepository

        service = TopicSuggesterService(conn)
        topics_repo = TopicsRepository(conn)

        if approve is not None:
            # Approve specific suggestion
            service.approve_suggestion(approve)
            console.print(f"[green]Approved suggestion #{approve}[/green]")
            conn.close()
            return

        if reject is not None:
            # Reject specific suggestion
            service.reject_suggestion(reject)
            console.print(f"[green]Rejected suggestion #{reject}[/green]")
            conn.close()
            return

        if approve_all:
            # Approve all suggestions above threshold
            count = service.approve_all_suggestions(min_confidence=min_confidence)
            console.print(f"[green]Approved {count} suggestions[/green]")
            conn.close()
            return

        # Show pending suggestions
        pending = topics_repo.get_pending_assignments(post_id=post_id)

        if not pending:
            if post_id:
                console.print(f"[yellow]No pending suggestions for post {post_id}[/yellow]")
            else:
                console.print("[yellow]No pending suggestions[/yellow]")
            conn.close()
            return

        # Display suggestions
        table = Table(title="Pending Topic Suggestions")
        table.add_column("ID", style="dim")
        table.add_column("Post", style="cyan")
        table.add_column("Topic", style="green")
        table.add_column("Confidence", justify="right")
        table.add_column("Suggested", style="dim")

        for p in pending:
            table.add_row(
                str(p['id']),
                p['post_id'][:12] + "..." if len(p['post_id']) > 12 else p['post_id'],
                p.get('topic_name', 'Unknown'),
                f"{p['confidence']:.2f}",
                str(p.get('suggested_at', ''))[:10]
            )

        console.print(table)
        console.print()
        console.print(f"[dim]Total: {len(pending)} suggestions[/dim]")
        console.print("[dim]Use --approve ID or --reject ID to act on suggestions[/dim]")

        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Review operation failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def due(
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Filter by topic name"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum posts to show"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """View posts due for review.

    SPAC-03: User can view currently due posts via CLI.
    D-04: Table format with truncated content.
    D-08: Themed reviews via --topic flag.

    Examples:
        xbm due
        xbm due --topic python
        xbm due --limit 20
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..services.review_service import ReviewService
        from ..repositories.topics import TopicsRepository

        service = ReviewService(conn)
        topics_repo = TopicsRepository(conn)

        # Resolve topic_id if topic name provided
        topic_id = None
        if topic:
            topic_obj = topics_repo.get_topic_by_name(topic)
            if not topic_obj:
                console.print(f"[red]Topic not found: {topic}[/red]")
                conn.close()
                raise typer.Exit(1)
            topic_id = topic_obj['id']

        # Get due posts
        posts = service.get_due_posts(topic_id=topic_id, limit=limit)

        if not posts:
            if topic:
                console.print(f"[yellow]No posts due for topic: {topic}[/yellow]")
            else:
                console.print("[yellow]No posts due for review[/yellow]")
            conn.close()
            return

        # Build table (D-04)
        table = Table(title="Due Posts" + (f" - {topic}" if topic else ""))
        table.add_column("#", style="dim", width=4)
        table.add_column("Author", style="cyan")
        table.add_column("Content Preview", style="white")
        table.add_column("Topics", style="green")
        table.add_column("Due", style="yellow")

        for i, post in enumerate(posts, 1):
            # Truncate content (D-04)
            text = post.get('text', '')
            preview = text[:50] + "..." if len(text) > 50 else text

            # Get topics for this post
            post_topics = topics_repo.get_post_topics(post['x_post_id'])
            topics_str = ", ".join(t['name'] for t in post_topics) or "None"

            # Format due date
            due_date = post.get('scheduled_for', '')
            if due_date:
                due_date = due_date[:10]  # Just the date

            table.add_row(
                str(i),
                f"@{post.get('author_username', 'unknown')}",
                preview,
                topics_str,
                due_date
            )

        console.print(table)
        console.print(f"[dim]Total: {len(posts)} posts due[/dim]")

        conn.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Failed to get due posts\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def review(
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Filter by topic name"),
    days: Optional[int] = typer.Option(None, "--days", "-d", help="Postpone days (for postpone action)"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="Database path"),
) -> None:
    """Start interactive review session for due posts.

    CLI-02: User can view resurfaced posts via CLI command.
    D-05: Notes displayed at top during review.
    D-06: Metadata shown (pub date, topics, review history).
    D-07: User chooses scheduling intent.
    D-10: Interactive one-at-a-time review session.

    Examples:
        xbm review
        xbm review --topic python
        xbm review --days 7  # Postpone all by 7 days
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..services.review_service import ReviewService
        from ..repositories.topics import TopicsRepository

        service = ReviewService(conn)
        topics_repo = TopicsRepository(conn)

        # Resolve topic_id if topic name provided
        topic_id = None
        if topic:
            topic_obj = topics_repo.get_topic_by_name(topic)
            if not topic_obj:
                console.print(f"[red]Topic not found: {topic}[/red]")
                conn.close()
                raise typer.Exit(1)
            topic_id = topic_obj['id']

        # Get due posts
        posts = service.get_due_posts(topic_id=topic_id)

        if not posts:
            if topic:
                console.print(f"[yellow]No posts due for topic: {topic}[/yellow]")
            else:
                console.print("[yellow]No posts due for review[/yellow]")
            console.print("[dim]Use 'xbm due' to see upcoming reviews[/dim]")
            conn.close()
            return

        console.print(f"[bold green]Starting review session[/bold green]")
        console.print(f"[dim]{len(posts)} posts due for review[/dim]")
        console.print()

        # Review each post
        reviewed_count = 0
        for post in posts:
            # Get topics for this post
            post_topics = topics_repo.get_post_topics(post['x_post_id'])

            # Build extra metadata for review-specific fields
            review_count = post.get('review_count', 0)
            last_review = post.get('last_reviewed')
            last_review_str = "Never" if not last_review else last_review[:10]
            user_pref = post.get('user_preference') or "None"

            extra_metadata = [
                ("Reviews", str(review_count)),
                ("Last Review", last_review_str),
                ("User Pref", user_pref),
            ]

            # Display post using shared module
            from .display import display_post
            display_post(console, post, topics=post_topics, extra_metadata=extra_metadata)
            console.print()

            # D-07: Prompt for scheduling choice
            console.print("[bold]Choose scheduling:[/bold]")
            console.print("  [1] Keep fresh (3 days)")
            console.print("  [2] Review again soon (2 weeks)")
            console.print("  [3] Review later (2 months)")
            console.print("  [s] Skip")
            console.print("  [p] Postpone")
            console.print()

            choice = typer.prompt("Choice", default="2")

            if choice.lower() == 's':
                console.print("[dim]Skipped[/dim]")
                console.print()
                continue

            if choice.lower() == 'p':
                # Postpone
                postpone_days = days or typer.prompt("Postpone days", type=int, default=7)
                next_date = service.process_postpone(post['x_post_id'], postpone_days)
                console.print(f"[yellow]Postponed for {postpone_days} days (until {next_date.strftime('%Y-%m-%d')})[/yellow]")
            else:
                # Map choice to user_choice
                choice_map = {'1': 'fresh', '2': 'soon', '3': 'later'}
                user_choice = choice_map.get(choice, 'soon')

                next_date = service.process_review_choice(post['x_post_id'], user_choice)
                console.print(f"[green]Scheduled for {next_date.strftime('%Y-%m-%d')}[/green]")

            reviewed_count += 1
            console.print()

        console.print(f"[bold green]Review session complete![/bold green]")
        console.print(f"[dim]Reviewed {reviewed_count} posts[/dim]")

        conn.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Review session failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def stats(
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Display post statistics and review progress.

    Shows:
    - Date range of posts (oldest to newest)
    - Total posts count
    - Posts per month breakdown
    - Review statistics and progress

    Examples:
        xbm stats
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..services.review_service import ReviewService
        from ..repositories.posts import PostsRepository

        posts_repo = PostsRepository(conn)
        service = ReviewService(conn)

        # Get post statistics
        post_stats = posts_repo.get_post_stats()
        review_stats = service.get_review_stats()

        # Display post statistics section
        console.print()
        console.print(Panel(
            Text.assemble(
                ("Post Statistics", "bold cyan"),
            ),
            border_style="cyan",
        ))

        # Date range line
        if post_stats['total'] > 0:
            console.print(f"  [dim]Date Range:[/dim] {post_stats['oldest_date']} to {post_stats['newest_date']}")
            console.print(f"  [dim]Total Posts:[/dim] {post_stats['total']}")
            console.print()

            # Posts by month (like Claude's context usage display)
            if post_stats['by_month']:
                console.print("  [bold]Posts by Month:[/bold]")
                console.print()

                # Calculate max for bar scaling
                max_count = max(post_stats['by_month'].values()) if post_stats['by_month'] else 1
                bar_width = 20  # Max bar width in characters

                # Sort months descending (most recent first)
                sorted_months = sorted(post_stats['by_month'].items(), key=lambda x: x[0], reverse=True)

                for month, count in sorted_months:
                    # Calculate bar length
                    bar_len = int((count / max_count) * bar_width) if max_count > 0 else 0
                    bar = "█" * bar_len + "░" * (bar_width - bar_len)

                    # Calculate percentage
                    pct = (count / post_stats['total']) * 100 if post_stats['total'] > 0 else 0

                    # Format: "  2026-05 ████████░░░░░░░░░░░░ 12 (12%)"
                    console.print(f"    {month} {bar} {count} ({pct:.0f}%)")

                console.print()
        else:
            console.print("  [dim]No posts in database[/dim]")
            console.print()

        # Display review statistics section
        console.print(Panel(
            Text.assemble(
                ("Review Statistics", "bold yellow"),
            ),
            border_style="yellow",
        ))

        # Build stats table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Total Posts", str(review_stats['total_posts']))
        table.add_row("Posts Due", str(review_stats['due_count']))
        table.add_row("Posts Reviewed", str(review_stats['reviewed_count']))

        # Calculate percentage
        if review_stats['total_posts'] > 0:
            reviewed_pct = (review_stats['reviewed_count'] / review_stats['total_posts']) * 100
            table.add_row("Review Progress", f"{reviewed_pct:.1f}%")
        else:
            table.add_row("Review Progress", "N/A")

        console.print(table)

        # Show encouragement message
        if review_stats['due_count'] > 0:
            console.print()
            console.print(f"[bold yellow]{review_stats['due_count']} posts awaiting review[/bold yellow]")
            console.print("[dim]Use 'xbm review' to start reviewing[/dim]")
        elif review_stats['total_posts'] > 0:
            console.print()
            console.print("[bold green]All caught up![/bold green]")
            console.print("[dim]No posts due for review[/dim]")

        console.print()
        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Failed to get statistics\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def reset(
    post_id: str = typer.Argument(..., help="X post ID to reset"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Reset review state for a specific post.

    D-13: Reset review state without re-syncing everything.
    Clears scheduling state and allows re-seeding from publication date.

    Examples:
        xbm reset 1234567890
        xbm reset 1234567890 --yes  # Skip confirmation
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..services.review_service import ReviewService
        from ..repositories.posts import PostsRepository
        from rich.prompt import Confirm

        service = ReviewService(conn)
        posts_repo = PostsRepository(conn)

        # Verify post exists
        post = posts_repo.get_by_id(post_id)
        if not post:
            console.print(f"[red]Post not found: {post_id}[/red]")
            conn.close()
            raise typer.Exit(1)

        # Confirmation prompt
        if not yes:
            console.print(f"[bold]Post:[/bold] @{post.get('author_username', 'unknown')}")
            text_preview = post.get('text', '')[:100]
            if text_preview:
                console.print(f"[dim]{text_preview}...[/dim]")
            console.print()

            if not Confirm.ask(f"Reset review state for post {post_id}?"):
                console.print("[yellow]Cancelled[/yellow]")
                conn.close()
                raise typer.Exit(0)

        # Reset state
        service.reset_review_state(post_id)

        console.print(f"[green]Reset review state for post {post_id}[/green]")
        console.print("[dim]State will be re-seeded from publication date on next review[/dim]")

        conn.close()

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Failed to reset review state\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        sys.exit(1)


@app.command()
def seed(
    force: bool = typer.Option(False, "--force", "-f", help="Re-seed all posts (clear existing)"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Initialize review state for posts without state.

    D-02: Seeds from publication date.
    Posts without review state get initial scheduled_for date.

    Examples:
        xbm seed
        xbm seed --force  # Re-seed all posts
    """
    try:
        if db_path is None:
            try:
                settings = Settings()
                db_path = settings.database_path
            except Exception:
                db_path = Path("data/bookmarks.db")

        conn = init_database(db_path)
        from ..services.review_service import ReviewService

        service = ReviewService(conn)

        if force:
            # Clear all existing review states
            conn.execute("DELETE FROM post_review_state")
            conn.commit()
            console.print("[yellow]Cleared all existing review states[/yellow]")

        # Seed new posts
        seeded_count = service.seed_new_posts()

        if seeded_count == 0:
            console.print("[green]All posts already have review state[/green]")
        else:
            console.print(f"[green]Seeded review state for {seeded_count} posts[/green]")
            console.print("[dim]Posts scheduled based on publication date (older posts due sooner)[/dim]")

        conn.close()

    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Failed to seed review states\n", "bold red"),
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