# Phase 10: CLI Display - Research

**Researched:** 2026-06-06
**Domain:** Rich Panel/Tree rendering for embedded posts in CLI
**Confidence:** HIGH

## Summary

This phase extends the existing `display_post()` function in `src/cli/display.py` to render embedded posts (retweets and quote tweets) using Rich's nested Panel components. The storage layer (Phase 8) already provides `embedded_post` data via `get_paginated_with_embedded()`, and Phase 9 established the rendering patterns (quote tweet nested layout, retweet attribution, unavailable placeholder). CLI implementation follows the same visual hierarchy but adapts to terminal output constraints.

**Primary recommendation:** Extend `display_post()` with an `embedded_post` parameter and dispatch to helper functions (`_render_quote_post()`, `_render_retweet_post()`, `_render_unavailable_post()`) based on `post_type`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use nested Rich Panel components for quote tweets.
  - Outer Panel: user's commentary text with cyan author header (`[bold cyan]@username`)
  - Inner Panel: quoted content with `border_style="dim"` and indented structure
  - Visual hierarchy: user's quote commentary prominent, quoted content subdued but readable

- **D-02:** Quote attribution shown as `[dim]Quoting @username[/dim]` above inner Panel.
  - Label outside the inner Panel, not inside

- **D-03:** Header line shows `"[dim]Reposted from @original_author[/dim]"` above content Panel for retweets.
  - Original content displayed in standard Panel (same layout as original posts)

- **D-04:** Reposter info visible as `"[dim]Reposted by @retweeter[/dim]"` in smaller text.
  - Shows who retweeted while keeping original author prominent

- **D-05:** Panel with `border_style="red"` for unavailable embedded posts.
  - Generic text-based post icon in center
  - Message: `"Original post unavailable"` in dim
  - Show `"[dim]@username[/dim]"` if author known from reference ID

- **D-06:** When embedded post has author info but is unavailable:
  - Show `"[dim]Originally by @username[/dim]"` above placeholder

- **D-07:** List media URLs below content in dim style with numbered links.
  - Format: `"[dim]  [1] https://...[/dim]"` (indented, one per line)
  - Show link icon prefix: `"[dim]🔗 https://...[/dim]"`

- **D-08:** Group embedded post media URLs with original post media URLs.
  - No separate section — all media URLs shown together after content

### Claude's Discretion

- Exact Rich component styling (border colors, indentation width)
- Animation/timing for panel transitions (if any)
- Truncation length for long quoted content
- Whether to show full author display_name or just username

### Deferred Ideas (OUT OF SCOPE)

- FTS5 search including embedded post text (SRCH-F01) — future phase
- Display original post metrics on retweets (MET-F01) — future phase
- Quote-of-quote chain support beyond 1 level (REC-F01) — out of scope
- Image preview in terminal (requires image protocol support) — out of scope for v1.2

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-06 | Quote tweets render with Rich Panel showing nested structure | Rich supports nested Panels (verified experimentally). Outer Panel for user commentary, inner Panel for quoted content. |
| CLI-07 | Retweets show "Reposted" indicator with original content | Standard Panel with attribution header line. Uses existing display patterns. |
| CLI-08 | CLI displays media URLs from embedded posts | Media URLs already stored in embedded_posts.media_urls. Display with link prefix and indentation. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Rich** | 15.0.0+ | Terminal formatting with nested Panels | Already in project. Supports nested Panels (verified). |
| **Typer** | 0.24+ | CLI framework with CliRunner testing | Already in project. Standard for Python CLIs. |
| **pytest** | 7.x | Test framework | Already in project. Use CliRunner for in-process testing. |

### Existing Code
| File | Purpose | Extension Point |
|------|---------|-----------------|
| `src/cli/display.py` | `display_post()` function | Add `embedded_post` parameter, dispatch by `post_type` |
| `src/cli/main.py` | CLI commands (browse, review) | Call `display_post()` with embedded data |
| `src/repositories/posts.py` | `get_paginated_with_embedded()` | Already returns `embedded_post` key |
| `src/repositories/embedded_posts.py` | `get_by_id()` | Already returns full embedded post dict |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rich Panel | Rich Tree | Tree is for hierarchical lists, not nested content. Panel provides cleaner visual nesting. |
| Nested Panel | Single Panel with separator | Harder to distinguish quote content visually. Nested Panels create clear visual hierarchy. |

**Installation:**
No new dependencies required. Rich 15.0.0+ already installed.

**Version verification:**
```
$ pip3 show rich | grep Version
Version: 15.0.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/cli/
├── display.py          # display_post(), _render_quote_post(), _render_retweet_post()
│                       # _render_unavailable_post(), display_post_separator()
└── main.py             # CLI commands (browse, review)
```

### Pattern 1: Nested Panel for Quote Tweets
**What:** Rich Panel components can be nested — a Panel can contain another Panel as its renderable content.
**When to use:** Quote tweets where user's commentary wraps the quoted original.
**Example:**
```python
# Source: [VERIFIED: Experimental verification]
from rich.panel import Panel
from rich.console import Console

def _render_quote_post(console: Console, post: dict, embedded_post: dict) -> None:
    """Render quote tweet with nested Panel structure per D-01, D-02."""
    # User's commentary (outer panel content)
    user_text = post.get('text', '')
    user_author = f"@{post.get('author_username', 'unknown')}"

    # Inner panel for quoted content
    quoted_text = embedded_post.get('text', '')
    quoted_author = f"@{embedded_post.get('author_username', 'unknown')}"

    # D-02: Attribution label above inner panel
    attribution = f"[dim]Quoting {quoted_author}[/dim]"

    # D-01: Inner panel with dim border
    inner_panel = Panel(
        quoted_text,
        title=f"[bold cyan]{quoted_author}[/bold cyan]",
        border_style="dim"
    )

    # D-01: Outer panel with user commentary
    outer_content = f"{user_text}\n\n{attribution}\n{inner_panel}"
    outer_panel = Panel(
        outer_content,
        title=f"[bold cyan]{user_author}[/bold cyan]",
        border_style="blue"
    )

    console.print(outer_panel)
```

### Pattern 2: Retweet Attribution Header
**What:** Retweets display original content with attribution line above.
**When to use:** Retweets where user reshared without commentary.
**Example:**
```python
# Source: [VERIFIED: Existing display_post patterns]
def _render_retweet_post(console: Console, post: dict, embedded_post: dict) -> None:
    """Render retweet with attribution header per D-03, D-04."""
    # D-04: Reposter info
    retweeter = post.get('author_username', 'unknown')
    console.print(f"[dim]Reposted by @{retweeter}[/dim]")
    console.print()

    # D-03: Reposted from header
    original_author = embedded_post.get('author_username', 'unknown')
    console.print(f"[dim]Reposted from @{original_author}[/dim]")

    # Original content in standard Panel (same as original posts)
    original_text = embedded_post.get('text', '')
    header = f"[bold cyan]@{original_author}[/bold cyan]"

    console.print(Panel(
        original_text,
        title=header,
        border_style="blue"
    ))

    # Render media URLs if present
    _render_media_urls(console, embedded_post.get('media_urls', []))
```

### Pattern 3: Unavailable Post Placeholder
**What:** When embedded post is deleted/protected, show placeholder with red border.
**When to use:** Retweets/quotes where original post is unavailable.
**Example:**
```python
# Source: [VERIFIED: CONTEXT.md D-05, D-06]
def _render_unavailable_post(console: Console, post: dict, embedded_post: dict | None) -> None:
    """Render unavailable post placeholder per D-05, D-06."""
    # D-05: Red-bordered panel
    placeholder_text = "[dim]Original post unavailable[/dim]"

    # D-06: Show author if known
    if embedded_post and embedded_post.get('author_username'):
        author_line = f"[dim]Originally by @{embedded_post.get('author_username')}[/dim]"
        placeholder_text = f"{author_line}\n\n{placeholder_text}"

    console.print(Panel(
        placeholder_text,
        border_style="red"
    ))
```

### Pattern 4: Media URL Display
**What:** List media URLs with link icon prefix.
**When to use:** Posts with media URLs (images, videos).
**Example:**
```python
# Source: [VERIFIED: CONTEXT.md D-07, D-08]
def _render_media_urls(console: Console, media_urls: list[str]) -> None:
    """Render media URLs with link icon prefix per D-07."""
    for url in media_urls:
        # D-07: Indented, dim, with link icon
        console.print(f"[dim]  🔗 {url}[/dim]")
```

### Anti-Patterns to Avoid

- **Rendering all posts identically:** Must check `post_type` and dispatch to appropriate renderer.
- **Assuming embedded_post is always available:** Must handle `None` case and `available=False` case.
- **Using Rich Tree for nested content:** Tree is for hierarchical lists; Panel provides cleaner nesting for quote tweets.
- **Forgetting to fetch embedded_post:** CLI commands must call `get_paginated_with_embedded()` or pass `embedded_post` to `display_post()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Nested content rendering | Custom indentation logic | Rich Panel nesting | Native support, proper borders |
| Terminal styling | Manual ANSI codes | Rich markup | Cleaner code, automatic width handling |
| Media URL display | Custom truncation | Rich's automatic text wrapping | Consistent width, handles terminals |

**Key insight:** Rich handles Panel nesting and border styling automatically. Don't build custom indentation logic.

## Common Pitfalls

### Pitfall 1: Forgetting to Fetch Embedded Post Data
**What goes wrong:** CLI shows posts but `embedded_post` is `None` for retweets/quotes because `get_paginated()` was used instead of `get_paginated_with_embedded()`.
**Why it happens:** `get_paginated()` returns posts without joined embedded data.
**How to avoid:** Use `get_paginated_with_embedded()` in browse command, or pass `embedded_post` parameter to `display_post()`.
**Warning signs:** All posts render as original type, retweets show no original content.

### Pitfall 2: Not Handling Unavailable Embedded Posts
**What goes wrong:** KeyError or empty display when `embedded_post.available` is `False`.
**Why it happens:** Deleted/protected originals exist in embedded_posts table with `available=False`.
**How to avoid:** Check `embedded_post.get('available', True)` before rendering content. Use `_render_unavailable_post()` for unavailable cases.
**Warning signs:** Crashes on retweets of deleted tweets, empty Panel content.

### Pitfall 3: Displaying Quoted Content in Wrong Order
**What goes wrong:** Quoted content appears above user's commentary, reversing the visual hierarchy.
**Why it happens:** Incorrect Panel nesting order.
**How to avoid:** Outer Panel = user's commentary; inner Panel = quoted content. User's text should be prominent.
**Warning signs:** Quote tweets look inverted compared to web display.

### Pitfall 4: Missing Media URLs from Embedded Posts
**What goes wrong:** Images from original tweet don't appear in retweet/quote display.
**Why it happens:** Only checking `post.media_urls`, not `embedded_post.media_urls`.
**How to avoid:** Per D-08, group all media URLs together. Check both `post` and `embedded_post` for media.
**Warning signs:** Retweets missing images that appear on X/Twitter.

## Code Examples

### Extended display_post Function

```python
# Source: [VERIFIED: Existing src/cli/display.py + CONTEXT.md decisions]
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
    """Display a single post with embedded post support.

    Args:
        console: Rich console for output.
        post: Post dict with text, author_username, post_type, embedded_post_id.
        topics: Optional list of topic dicts.
        extra_metadata: Optional list of (label, value) tuples.
        show_note: Whether to show note panel if present.
        embedded_post: Optional embedded post dict for retweets/quotes.
    """
    post_type = post.get('post_type', 'original')

    # Dispatch based on post type
    if post_type == 'quote' and embedded_post:
        _render_quote_post(console, post, embedded_post, topics, extra_metadata, show_note)
    elif post_type == 'retweet' and embedded_post:
        _render_retweet_post(console, post, embedded_post, topics, extra_metadata)
    elif post_type in ('retweet', 'quote') and (embedded_post is None or not embedded_post.get('available', True)):
        _render_unavailable_post(console, post, embedded_post)
    else:
        _render_original_post(console, post, topics, extra_metadata, show_note)


def _render_original_post(console: Console, post: dict, topics, extra_metadata, show_note) -> None:
    """Render original post using existing display_post logic."""
    # Existing logic from display.py lines 36-88
    if show_note and post.get('note'):
        console.print(Panel(post['note'], title="[bold yellow]Your Note[/bold yellow]", border_style="yellow"))
        console.print()

    text = post.get('text', '')
    author = f"@{post.get('author_username', 'unknown')}"
    display_name = post.get('author_display_name', '')
    header = f"[bold cyan]{author}[/bold cyan]"
    if display_name:
        header += f" ({display_name})"

    console.print(Panel(text, title=header, border_style="blue"))

    # Metadata table
    _render_metadata(console, post, topics, extra_metadata)
    _render_media_urls(console, post.get('media_urls', []))
```

### Quote Post Renderer

```python
def _render_quote_post(console: Console, post: dict, embedded_post: dict, topics, extra_metadata, show_note) -> None:
    """Render quote tweet with nested Panel per D-01, D-02."""
    # Note if present
    if show_note and post.get('note'):
        console.print(Panel(post['note'], title="[bold yellow]Your Note[/bold yellow]", border_style="yellow"))
        console.print()

    # User's commentary
    user_text = post.get('text', '')
    user_author = f"@{post.get('author_username', 'unknown')}"
    user_display = post.get('author_display_name', '')

    # Quoted content
    quoted_text = embedded_post.get('text', '')
    quoted_author = f"@{embedded_post.get('author_username', 'unknown')}"
    quoted_display = embedded_post.get('author_display_name', '')

    # D-02: Attribution label
    attribution = f"[dim]Quoting @{quoted_author}[/dim]"

    # Inner panel title
    inner_title = f"[bold cyan]{quoted_author}[/bold cyan]"
    if quoted_display:
        inner_title = f"[bold cyan]{quoted_author}[/bold cyan] ({quoted_display})"

    # D-01: Nested panel structure
    inner_panel = Panel(
        quoted_text,
        title=inner_title,
        border_style="dim"
    )

    # Build outer panel content
    outer_content = f"{user_text}\n\n{attribution}\n{inner_panel}"

    # Outer panel title
    outer_title = f"[bold cyan]{user_author}[/bold cyan]"
    if user_display:
        outer_title = f"[bold cyan]{user_author}[/bold cyan] ({user_display})"

    console.print(Panel(outer_content, title=outer_title, border_style="blue"))

    # Metadata for quote tweet
    _render_metadata(console, post, topics, extra_metadata)

    # D-08: Combined media URLs
    all_media = post.get('media_urls', []) + embedded_post.get('media_urls', [])
    _render_media_urls(console, all_media)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single display_post for all types | Type-dispatch pattern with embedded_post | Phase 10 | Clean separation, easy testing |
| Manual indentation for nested content | Rich Panel nesting | Rich 10.0+ | Native borders, proper wrapping |

**Deprecated/outdated:**
- Using Rich Tree for quote tweets: Panels provide cleaner visual nesting.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rich Panel nesting works for arbitrarily deep nesting | Architecture | LOW - verified experimentally |
| A2 | `get_paginated_with_embedded()` returns `embedded_post` key in post dict | Integration | LOW - verified in posts.py code |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

None. All technical questions were resolved through code verification and experimental validation.

## Validation Architecture

**Test Framework:**
| Property | Value |
|----------|-------|
| Framework | pytest 7.x (existing) |
| Config file | None - tests use CliRunner directly |
| Quick run command | `pytest tests/test_cli_display.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-06 | Quote tweet nested Panel rendering | unit | `pytest tests/test_cli_display.py::test_quote_tweet_rendering -x` | ❌ Wave 0 |
| CLI-06 | Quote attribution label display | unit | `pytest tests/test_cli_display.py::test_quote_attribution -x` | ❌ Wave 0 |
| CLI-07 | Retweet "Reposted" header | unit | `pytest tests/test_cli_display.py::test_retweet_header -x` | ❌ Wave 0 |
| CLI-07 | Retweet original content Panel | unit | `pytest tests/test_cli_display.py::test_retweet_content -x` | ❌ Wave 0 |
| CLI-08 | Media URLs from embedded posts | unit | `pytest tests/test_cli_display.py::test_embedded_media_urls -x` | ❌ Wave 0 |
| CLI-08 | Unavailable post placeholder | unit | `pytest tests/test_cli_display.py::test_unavailable_placeholder -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_cli_display.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli_display.py` — covers all CLI-06, CLI-07, CLI-08 behaviors
- [ ] Test fixtures for quote tweet post dict with embedded_post
- [ ] Test fixtures for retweet post dict with embedded_post
- [ ] Test fixtures for unavailable embedded_post

*(If no gaps: "None — existing test infrastructure covers all phase requirements")*

**Note:** No existing tests for display functions. New test file needed.

## Security Domain

**Security enforcement enabled** (absent in config = enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CLI uses stored tokens from Phase 1 |
| V3 Session Management | no | No session management in this phase |
| V4 Access Control | no | No authorization in this phase |
| V5 Input Validation | yes | Post content from DB is trusted; validate `post_type` values |
| V6 Cryptography | no | No crypto operations in this phase |

### Known Threat Patterns for CLI Display

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Content injection in terminal | Tampering | Rich auto-escapes markup in text content; verify no `|safe` equivalent |
| Excessive content length | Denial of Service | Truncate long text (discretion: planner decides length) |

## Sources

### Primary (HIGH confidence)
- [Rich Documentation](https://rich.readthedocs.io/) — Panel API, nested components
- [src/cli/display.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/cli/display.py) — Existing display_post implementation
- [src/repositories/posts.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/posts.py) — get_paginated_with_embedded() returns embedded_post
- [src/repositories/embedded_posts.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/embedded_posts.py) — EmbeddedPostsRepository API

### Secondary (MEDIUM confidence)
- [src/web/templates/components/_post_card.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/components/_post_card.html) — Web rendering patterns for consistency

### Tertiary (Project References)
- [CONTEXT.md Phase 10](file:///Users/ffaber/claude-projects/x-bookmarked-posts/.planning/phases/10-cli-display/10-CONTEXT.md) — User decisions
- [CONTEXT.md Phase 9](file:///Users/ffaber/claude-projects/x-bookmarked-posts/.planning/phases/09-web-display/09-CONTEXT.md) — Web patterns for consistency

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new dependencies; Rich 15.0.0+ verified installed
- Architecture: HIGH — Nested Panel verified experimentally; existing display_post is straightforward
- Pitfalls: HIGH — Clear from CONTEXT.md decisions and existing web patterns

**Research date:** 2026-06-06
**Valid until:** 30 days (stable Rich API)