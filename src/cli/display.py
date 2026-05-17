"""Post display utilities for CLI commands.

Shared display logic for browse, review, and other commands
that show post content.

Usage:
    from src.cli.display import display_post
    display_post(console, post, topics)
"""

from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def display_post(
    console: Console,
    post: dict[str, Any],
    topics: Optional[list[dict[str, Any]]] = None,
    extra_metadata: Optional[list[tuple[str, str]]] = None,
    show_note: bool = True,
) -> None:
    """Display a single post in full-panel format.

    Args:
        console: Rich console for output.
        post: Post dict with text, author_username, author_display_name, created_at.
        topics: Optional list of topic dicts with 'name' key.
        extra_metadata: Optional list of (label, value) tuples for additional metadata.
        show_note: Whether to show note panel if present (default True).
    """
    # Display note if present
    if show_note:
        note = post.get('note')
        if note:
            console.print(Panel(
                note,
                title="[bold yellow]Your Note[/bold yellow]",
                border_style="yellow"
            ))
            console.print()

    # Display post content
    text = post.get('text', '')
    author = f"@{post.get('author_username', 'unknown')}"
    display_name = post.get('author_display_name', '')

    header = f"[bold cyan]{author}[/bold cyan]"
    if display_name:
        header += f" ({display_name})"

    console.print(Panel(
        text,
        title=header,
        border_style="blue"
    ))

    # Build metadata table
    metadata = Table(show_header=False, box=None, padding=(0, 2))
    metadata.add_column("Label", style="dim")
    metadata.add_column("Value", style="white")

    published = post.get('created_at', 'Unknown')
    if published:
        published = published[:10]
    metadata.add_row("Published", published)

    if topics is not None:
        topics_str = ", ".join(t['name'] for t in topics) or "None"
        metadata.add_row("Topics", topics_str)

    # Add extra metadata rows (e.g., Reviews, Last Review, User Pref)
    if extra_metadata:
        for label, value in extra_metadata:
            metadata.add_row(label, value)

    console.print(metadata)


def display_post_separator(console: Console) -> None:
    """Print a separator line between posts.

    Args:
        console: Rich console for output.
    """
    console.print()
    console.print("[dim]" + "─" * 60 + "[/dim]")