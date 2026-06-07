# Phase 10: CLI Display - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Render embedded posts (retweets and quote tweets) with clear visual hierarchy in terminal output using Rich Panel/Tree components. The CLI display handles three post types (original, retweet, quote) with distinct visual treatments for each.

This phase delivers:
- Quote tweet rendering with nested Panel structure
- Retweet rendering with repost attribution header
- Media URL display from embedded posts
- Unavailable post placeholder handling

**Out of scope (Phase 11+):**
- Cast receiver display of embedded posts (Phase 11)
- FTS5 search including embedded post text (future)
- Live retweet counts (out of scope per REQUIREMENTS.md)

</domain>

<decisions>
## Implementation Decisions

### Quote Tweet Layout
- **D-01:** Use nested Rich Panel components for quote tweets.
  - Outer Panel: user's commentary text with cyan author header (`[bold cyan]@username`)
  - Inner Panel: quoted content with `border_style="dim"` and indented structure
  - Visual hierarchy: user's quote commentary prominent, quoted content subdued but readable
  - Rationale: Matches web nested card pattern, Rich supports nested Panels natively.

- **D-02:** Quote attribution shown as `[dim]Quoting @username[/dim]` above inner Panel.
  - Label outside the inner Panel, not inside
  - Rationale: Signals relationship without competing with author display.

### Retweet Display
- **D-03:** Header line shows `"[dim]Reposted from @original_author[/dim]"` above content Panel.
  - Original content displayed in standard Panel (same layout as original posts)
  - Rationale: Clear attribution, consistent with existing `display_post()` Panel style.

- **D-04:** Reposter info visible as `"[dim]Reposted by @retweeter[/dim]"` in smaller text.
  - Shows who retweeted while keeping original author prominent
  - Rationale: Full context for why this post appeared in bookmarks.

### Unavailable Post Handling
- **D-05:** Panel with `border_style="red"` for unavailable embedded posts.
  - Generic text-based post icon in center
  - Message: `"Original post unavailable"` in dim
  - Show `"[dim]@username[/dim]"` if author known from reference ID
  - Rationale: Graceful degradation with visual distinction from available content.

- **D-06:** When embedded post has author info but is unavailable:
  - Show `"[dim]Originally by @username[/dim]"` above placeholder
  - Rationale: Partial information better than none.

### Media URL Display
- **D-07:** List media URLs below content in dim style with numbered links.
  - Format: `"[dim]  [1] https://...[/dim]"` (indented, one per line)
  - Show link icon prefix: `"[dim]🔗 https://...[/dim]"`
  - Rationale: Terminal can't display images inline; links allow user to open.

- **D-08:** Group embedded post media URLs with original post media URLs.
  - No separate section — all media URLs shown together after content
  - Rationale: Simpler display, user sees all links in one place.

### Claude's Discretion
- Exact Rich component styling (border colors, indentation width)
- Animation/timing for panel transitions (if any)
- Truncation length for long quoted content
- Whether to show full author display_name or just username

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — CLI-06, CLI-07, CLI-08 (CLI display requirements for Phase 10)
- `.planning/REQUIREMENTS.md` §Out of Scope — Live metrics, recursive quotes, thread context

### Prior Phase Context
- `.planning/phases/08-storage-foundation/08-CONTEXT.md` — Storage decisions, embedded_posts table structure, post_type column
- `.planning/phases/09-web-display/09-CONTEXT.md` — Web display patterns for quote tweets, retweets, unavailable handling

### Existing Code (from prior phases)
- `src/cli/display.py` — `display_post()` function with Panel/Table patterns
- `src/cli/main.py` — CLI commands (browse, review) using display module
- `src/repositories/posts.py` — `_row_to_dict()` returns `post_type` and `embedded_post_id`
- `src/repositories/embedded_posts.py` — `get_by_id()` for fetching embedded post data

### Architecture
- `CLAUDE.md` — Technology stack (Python, Typer, Rich)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **src/cli/display.py:display_post()** — Core display function using `Panel` for post content, `Table` for metadata
- **rich.panel.Panel** — Existing pattern: `Panel(text, title=header, border_style="blue")`
- **rich.table.Table** — Existing pattern: metadata table with dim labels
- **rich.console.Console** — Output handling with color support

### Established Patterns
- **Panel styling:** `border_style="blue"` for posts, `"yellow"` for notes, `"green"` for success
- **Author header:** `[bold cyan]@username[/bold cyan]` with optional display_name
- **Metadata format:** `Table` with dim label column, white value column
- **Link display:** `"[link={url}]{url}[/link]"` format for clickable links
- **Separator:** `"[dim]" + "─" * 60 + "[/dim]"` between posts

### Integration Points
- **src/cli/main.py:browse()** — Calls `display_post()` for each post, needs to check `post_type` and fetch embedded post
- **src/cli/main.py:review()** — Also uses `display_post()`, needs embedded post handling
- **src/repositories/posts.py** — Needs `get_paginated_with_embedded()` or similar method to JOIN embedded_posts
- **src/cli/display.py** — Extend `display_post()` to accept `embedded_post` parameter

</code_context>

<specifics>
## Specific Ideas

- Quote tweet: Outer Panel with cyan header → inner Panel with dim border showing quoted content
- Retweet: `"[dim]Reposted from @author[/dim]"` line → standard Panel with original content
- Unavailable: Red-bordered Panel with `"[dim]Original post unavailable[/dim]"` message
- Media URLs: Indented list below content, prefixed with 🔗 emoji

</specifics>

<deferred>
## Deferred Ideas

- FTS5 search including embedded post text (SRCH-F01) — future phase
- Display original post metrics on retweets (MET-F01) — future phase
- Quote-of-quote chain support beyond 1 level (REC-F01) — out of scope
- Image preview in terminal (requires image protocol support) — out of scope for v1.2

</deferred>

---
*Phase: 10-cli-display*
*Context gathered: 2026-06-06*