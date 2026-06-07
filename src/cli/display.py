"""Post display utilities for CLI commands.

Shared display logic for browse, review, and other commands
that show post content. Handles original posts, retweets, quote tweets,
and unavailable embedded posts.

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
    embedded_post: Optional[dict[str, Any]] = None,
) -> None:
    """Display a single post in full-panel format.

    Handles three post types:
    - original: Standard post display
    - retweet: Shows "Reposted from @user" header with original content
    - quote: Shows user's commentary with nested quoted content

    Args:
        console: Rich console for output.
        post: Post dict with text, author_username, author_display_name, created_at.
              Also includes post_type ('original', 'retweet', 'quote') for
              embedded post handling. May contain nested 'embedded_post' key.
        topics: Optional list of topic dicts with 'name' key.
        extra_metadata: Optional list of (label, value) tuples for additional metadata.
        show_note: Whether to show note panel if present (default True).
        embedded_post: Optional embedded post dict for retweets and quotes.
                       Contains original post content, author info, and availability.
                       If not provided, extracted from post['embedded_post'] if present.
    """
    # Extract embedded_post from post dict if not passed explicitly
    if embedded_post is None and 'embedded_post' in post:
        embedded_post = post.get('embedded_post')

    # T-10-01-01: Validate post_type
    post_type = post.get('post_type', 'original')
    if post_type not in ('original', 'retweet', 'quote'):
        # Invalid post_type, render as original
        post_type = 'original'

    # Dispatch based on post_type and embedded_post availability
    if post_type == 'quote' and embedded_post and embedded_post.get('available', True):
        _render_quote_post(console, post, embedded_post, topics, extra_metadata, show_note)
    elif post_type == 'retweet' and embedded_post and embedded_post.get('available', True):
        _render_retweet_post(console, post, embedded_post, topics, extra_metadata)
    elif post_type in ('retweet', 'quote') and (embedded_post is None or not embedded_post.get('available', True)):
        _render_unavailable_post(console, post, embedded_post)
    else:
        _render_original_post(console, post, topics, extra_metadata, show_note)


def _render_original_post(
    console: Console,
    post: dict[str, Any],
    topics: Optional[list[dict[str, Any]]] = None,
    extra_metadata: Optional[list[tuple[str, str]]] = None,
    show_note: bool = True,
) -> None:
    """Render an original post (not a retweet or quote).

    Args:
        console: Rich console for output.
        post: Post dict with text, author info, created_at.
        topics: Optional list of topic dicts.
        extra_metadata: Optional list of (label, value) tuples.
        show_note: Whether to show note panel if present.
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

    # Render metadata
    _render_metadata(console, post, topics, extra_metadata)

    # Render media URLs
    _render_media_urls(console, post.get('media_urls', []))


def _render_quote_post(
    console: Console,
    post: dict[str, Any],
    embedded_post: dict[str, Any],
    topics: Optional[list[dict[str, Any]]] = None,
    extra_metadata: Optional[list[tuple[str, str]]] = None,
    show_note: bool = True,
) -> None:
    """Render a quote tweet with nested original content.

    Per D-01, D-02: Outer panel for quoter's commentary,
    inner panel for quoted content with attribution.

    Args:
        console: Rich console for output.
        post: Quote tweet dict (user's commentary).
        embedded_post: Original quoted post dict.
        topics: Optional list of topic dicts.
        extra_metadata: Optional list of (label, value) tuples.
        show_note: Whether to show note panel if present.
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

    # D-01: Outer panel with quoter's commentary
    quoter = f"@{post.get('author_username', 'unknown')}"
    quoter_display = post.get('author_display_name', '')
    quoter_header = f"[bold cyan]{quoter}[/bold cyan]"
    if quoter_display:
        quoter_header += f" ({quoter_display})"

    quoter_text = post.get('text', '')

    console.print(Panel(
        quoter_text,
        title=quoter_header,
        border_style="blue"
    ))

    # D-02: Attribution line for quoted content
    quoted_author = embedded_post.get('author_username', 'unknown')
    console.print(f"[dim]Quoting @{quoted_author}[/dim]")

    # D-01: Inner panel with quoted content (dimmed border)
    quoted_text = embedded_post.get('text', '')
    quoted_display = embedded_post.get('author_display_name', '')
    quoted_header = f"[bold cyan]@{quoted_author}[/bold cyan]"
    if quoted_display:
        quoted_header += f" ({quoted_display})"

    console.print(Panel(
        quoted_text,
        title=quoted_header,
        border_style="dim"
    ))

    # Render metadata for quoter's post
    _render_metadata(console, post, topics, extra_metadata)

    # D-08: Combined media URLs from both quoter and quoted
    all_media_urls = post.get('media_urls', []) + embedded_post.get('media_urls', [])
    _render_media_urls(console, all_media_urls)


def _render_retweet_post(
    console: Console,
    post: dict[str, Any],
    embedded_post: dict[str, Any],
    topics: Optional[list[dict[str, Any]]] = None,
    extra_metadata: Optional[list[tuple[str, str]]] = None,
) -> None:
    """Render retweet with attribution header per D-03, D-04.

    Args:
        console: Rich console for output.
        post: Retweet post dict (contains retweeter info).
        embedded_post: Original post dict.
        topics: Optional list of topic dicts.
        extra_metadata: Optional list of (label, value) tuples.
    """
    # D-04: Reposter info
    retweeter = post.get('author_username', 'unknown')
    console.print(f"[dim]Reposted by @{retweeter}[/dim]")
    console.print()

    # D-03: Reposted from header
    original_author = embedded_post.get('author_username', 'unknown')
    console.print(f"[dim]Reposted from @{original_author}[/dim]")

    # Original content panel (same styling as original posts)
    original_text = embedded_post.get('text', '')
    display_name = embedded_post.get('author_display_name', '')
    header = f"[bold cyan]@{original_author}[/bold cyan]"
    if display_name:
        header += f" ({display_name})"

    console.print(Panel(
        original_text,
        title=header,
        border_style="blue"
    ))

    # Metadata table
    _render_metadata(console, embedded_post, topics, extra_metadata)

    # D-07, D-08: Media URLs and link URLs from embedded post
    _render_media_urls(console, embedded_post.get('media_urls', []))
    _render_media_urls(console, embedded_post.get('link_urls', []))


def _render_unavailable_post(
    console: Console,
    post: dict[str, Any],
    embedded_post: Optional[dict[str, Any]] = None,
) -> None:
    """Render unavailable embedded post placeholder per D-05, D-06.

    Args:
        console: Rich console for output.
        post: Post dict (retweet or quote).
        embedded_post: Embedded post dict or None if completely unavailable.
    """
    # D-05: Red-bordered panel with generic message
    placeholder_text = "[dim]Original post unavailable[/dim]"

    # D-06: Show author if known from embedded_post
    if embedded_post and embedded_post.get('author_username'):
        author_line = f"[dim]Originally by @{embedded_post.get('author_username')}[/dim]"
        placeholder_text = f"{author_line}\n\n{placeholder_text}"

    console.print(Panel(
        placeholder_text,
        border_style="red"
    ))


def _render_media_urls(console: Console, media_urls: list[str]) -> None:
    """Render media URLs with link icon prefix per D-07.

    Args:
        console: Rich console for output.
        media_urls: List of media URL strings.
    """
    if not media_urls:
        return

    for url in media_urls:
        # D-07: Indented, dim, with link icon
        console.print(f"[dim]  🔗 {url}[/dim]")


def _render_metadata(
    console: Console,
    post: dict[str, Any],
    topics: Optional[list[dict[str, Any]]] = None,
    extra_metadata: Optional[list[tuple[str, str]]] = None,
) -> None:
    """Render metadata table for a post.

    Args:
        console: Rich console for output.
        post: Post dict.
        topics: Optional list of topic dicts.
        extra_metadata: Optional list of (label, value) tuples.
    """
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

    # Add link to original post
    post_id = post.get('x_post_id', '')
    author_handle = post.get('author_username', '')
    if post_id and author_handle:
        link = f"https://x.com/{author_handle}/status/{post_id}"
        metadata.add_row("Link", f"[link={link}]{link}[/link]")

    # Add extra metadata rows
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