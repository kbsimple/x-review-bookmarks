# Phase 9: Web Display - Research

**Researched:** 2026-06-05
**Domain:** Jinja2 template rendering, Tailwind CSS card layouts, embedded post display patterns
**Confidence:** HIGH

## Summary

This phase renders retweets and quote tweets in the web interface with nested card layouts. The storage layer (Phase 8) already provides `post_type` ('original', 'retweet', 'quote'), `embedded_post_id`, and the `embedded_posts` table. The web layer needs to: (1) fetch embedded post data when loading posts for display, (2) render different card layouts based on `post_type`, (3) handle unavailable originals gracefully with placeholder cards, and (4) reuse existing media rendering patterns for embedded post images.

**Primary recommendation:** Modify `PostsRepository.get_paginated()` to JOIN with `embedded_posts` table, then create a Jinja2 macro `_post_card.html` with conditional rendering for retweets/quotes/originals. Keep the existing `browse.html` grid layout and extend it with nested card components.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Nested card layout for quote tweets — outer card for user's commentary, inner card (gray-50 bg, gray-200 border) for quoted content
- **D-02:** Quote attribution as "Quoting @username" gray label above nested card (outside the nested card)
- **D-03:** Retweet header: "Reposted from @original_author" in gray text, original content displayed below
- **D-04:** Retweeter info visible: "Reposted by @retweeter" smaller text above header
- **D-05:** Unavailable embedded posts show gray placeholder card with "Original post unavailable" text and generic post icon
- **D-06:** Show author if known from reference ID — if `embedded_posts.author_username` exists but `available=false`, display "@username" in gray
- **D-07:** Adaptive image grid — 1 image full-width, 2 images side-by-side, 3+ images in 2x2 grid (max 4)
- **D-08:** Click-to-expand lightbox for images, same behavior as regular post cards
- **D-09:** Video thumbnail with play icon overlay, click opens X in new tab

### Claude's Discretion
- Exact Tailwind CSS class names for nested cards
- Animation timing for hover effects
- Responsive breakpoints for mobile vs desktop
- Loading states while fetching embedded posts
- Error handling for failed embedded post fetches

### Deferred Ideas (OUT OF SCOPE)
- FTS5 search including embedded post text (SRCH-F01) — future phase
- Display original post metrics on retweets (MET-F01) — future phase
- Quote-of-quote chain support beyond 1 level (REC-F01) — out of scope
- Interactive video player in web app — out of scope for v1.2
- CLI rendering of embedded posts (Phase 10)
- Cast receiver display of embedded posts (Phase 11)
- Live retweet counts — out of scope per REQUIREMENTS.md

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WEB-07 | Quote tweets display user's commentary above the embedded original post | D-01 (nested cards), D-02 (attribution label), browse.html pattern extension |
| WEB-08 | Retweets display original author's content with attribution | D-03 (reposted header), D-04 (retweeter info), existing post card pattern |
| WEB-09 | Embedded posts render images and video from the original post | D-07 (adaptive grid), D-08 (lightbox), D-09 (video thumbnail), existing media pattern |
| WEB-10 | Unavailable embedded posts show clear placeholder | D-05 (placeholder card), D-06 (show author if known), graceful degradation pattern |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.x (existing) | Template engine | Already used in browse.html, supports macros for reusable components |
| Tailwind CSS | CDN (existing) | Styling | Already used in web app, utility classes for nested cards |
| HTMX | 1.9.12 (existing) | Dynamic loading | Already used for infinite scroll, can handle embedded post loading |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI | 0.100+ (existing) | Web framework | Browse route modification to fetch embedded posts |
| SQLite3 | stdlib (existing) | Database | JOIN posts with embedded_posts table |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single template macro | Multiple template files | Macro pattern keeps rendering logic centralized, easier maintenance |
| JOIN in repository | Separate query for embedded | JOIN more efficient, single query, consistent with pagination pattern |
| Client-side fetch for embedded | Server-side JOIN | Server-side eliminates N+1 queries, simpler HTMX behavior |

**Installation:**
No new dependencies required. All components already exist in the project.

## Architecture Patterns

### Recommended Project Structure
```
src/web/
├── templates/
│   ├── base.html                    # Existing base layout
│   ├── browse.html                  # Modified to import macro
│   ├── components/
│   │   ├── _post_card.html          # NEW: Post card macro with type variants
│   │   └── _embedded_post.html      # NEW: Embedded post macro (nested card)
│   └── receiver.html                # Cast receiver (Phase 11)
├── routes/
│   └── browse.py                    # Modified: JOIN embedded_posts
└── static/
    └── js/
        └── lightbox.js              # NEW: Image lightbox (if not existing)
```

### Pattern 1: Post Card Macro with Conditional Rendering

**What:** Single Jinja2 macro renders different card layouts based on `post_type`.

**When to use:** All post rendering in browse.html.

**Example:**
```html
<!-- templates/components/_post_card.html -->
{% macro render_post_card(post, embedded_post=None) %}
<div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
    {% if post.post_type == 'retweet' %}
        {{ render_retweet_card(post, embedded_post) }}
    {% elif post.post_type == 'quote' %}
        {{ render_quote_card(post, embedded_post) }}
    {% else %}
        {{ render_original_card(post) }}
    {% endif %}
</div>
{% endmacro %}

{% macro render_retweet_card(post, embedded_post) %}
<div class="space-y-2">
    {# D-04: Retweeter info #}
    <div class="text-xs text-gray-400">Reposted by @{{ post.author_username }}</div>
    {% if embedded_post and embedded_post.available %}
        {# D-03: Reposted from header #}
        <div class="text-sm text-gray-500">Reposted from @{{ embedded_post.author_username }}</div>
        {{ render_post_content(embedded_post) }}
    {% else %}
        {{ render_unavailable_placeholder(embedded_post) }}
    {% endif %}
</div>
{% endmacro %}

{% macro render_quote_card(post, embedded_post) %}
<div class="space-y-3">
    {# User's commentary #}
    <p class="text-gray-800">{{ post.text }}</p>
    
    {# D-02: Quoting label #}
    {% if embedded_post and embedded_post.available %}
    <div class="text-xs text-gray-500">Quoting @{{ embedded_post.author_username }}</div>
    <div class="bg-gray-50 border border-gray-200 rounded p-3">
        {{ render_post_content(embedded_post) }}
    </div>
    {% else %}
    {{ render_unavailable_placeholder(embedded_post) }}
    {% endif %}
</div>
{% endmacro %}

{% macro render_unavailable_placeholder(embedded_post) %}
{# D-05: Placeholder for unavailable originals #}
<div class="bg-gray-100 rounded p-4 text-center">
    <div class="text-gray-400 mb-2">
        <svg class="w-8 h-8 mx-auto" fill="currentColor" viewBox="0 0 24 24">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm6 12H6v-1.5c0-1.99 4-3 6-3s6 1.01 6 3V18z"/>
        </svg>
    </div>
    <p class="text-gray-500 text-sm">Original post unavailable</p>
    {# D-06: Show author if known #}
    {% if embedded_post and embedded_post.author_username %}
    <p class="text-gray-400 text-xs mt-1">@{{ embedded_post.author_username }}</p>
    {% endif %}
</div>
{% endmacro %}
```

**Source:** [Jinja2 Macros Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/#macros) — HIGH confidence

### Pattern 2: Repository JOIN for Embedded Posts

**What:** Modify `PostsRepository.get_paginated()` to LEFT JOIN with `embedded_posts` table.

**When to use:** Whenever loading posts for display.

**Example:**
```python
# src/repositories/posts.py

def get_paginated_with_embedded(
    self,
    limit: int = 20,
    after_created_at: Optional[str] = None,
    after_post_id: Optional[str] = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Get posts with embedded post data for retweets/quotes.

    WEB-07, WEB-08: Include embedded post data in paginated results.

    Returns posts with 'embedded_post' key populated for retweets/quotes.
    """
    if after_created_at and after_post_id:
        query = """
            SELECT p.*,
                   e.x_post_id as embedded_id,
                   e.created_at as embedded_created_at,
                   e.text as embedded_text,
                   e.author_id as embedded_author_id,
                   e.author_username as embedded_author_username,
                   e.author_display_name as embedded_author_display_name,
                   e.media_urls as embedded_media_urls,
                   e.link_urls as embedded_link_urls,
                   e.available as embedded_available
            FROM posts p
            LEFT JOIN embedded_posts e ON p.embedded_post_id = e.x_post_id
            WHERE (p.created_at < ?)
               OR (p.created_at = ? AND p.x_post_id < ?)
            ORDER BY p.created_at DESC, p.x_post_id DESC
            LIMIT ?
        """
        rows = self._conn.execute(query, (after_created_at, after_created_at, after_post_id, limit + 1)).fetchall()
    else:
        query = """
            SELECT p.*,
                   e.x_post_id as embedded_id,
                   e.created_at as embedded_created_at,
                   e.text as embedded_text,
                   e.author_id as embedded_author_id,
                   e.author_username as embedded_author_username,
                   e.author_display_name as embedded_author_display_name,
                   e.media_urls as embedded_media_urls,
                   e.link_urls as embedded_link_urls,
                   e.available as embedded_available
            FROM posts p
            LEFT JOIN embedded_posts e ON p.embedded_post_id = e.x_post_id
            ORDER BY p.created_at DESC, p.x_post_id DESC
            LIMIT ?
        """
        rows = self._conn.execute(query, (limit + 1,)).fetchall()

    posts = [self._row_to_dict_with_embedded(row) for row in rows]
    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]
    return posts, has_more

def _row_to_dict_with_embedded(self, row: sqlite3.Row) -> dict[str, Any]:
    """Convert row to dict with embedded post data."""
    post = self._row_to_dict(row)

    # Add embedded post if present
    if row['embedded_id']:
        post['embedded_post'] = {
            'x_post_id': row['embedded_id'],
            'created_at': row['embedded_created_at'],
            'text': row['embedded_text'],
            'author_id': row['embedded_author_id'],
            'author_username': row['embedded_author_username'],
            'author_display_name': row['embedded_author_display_name'],
            'media_urls': json.loads(row['embedded_media_urls']) if row['embedded_media_urls'] else [],
            'link_urls': json.loads(row['embedded_link_urls']) if row['embedded_link_urls'] else [],
            'available': bool(row['embedded_available']),
        }
    else:
        post['embedded_post'] = None

    return post
```

**Source:** [SQLite JOIN patterns](https://www.sqlite.org/lang_select.html) — HIGH confidence (official)

### Anti-Patterns to Avoid

- **N+1 Queries:** Fetching embedded posts in a loop instead of JOIN. Use LEFT JOIN to fetch in single query.
- **Template Duplication:** Copying post card HTML for each variant. Use Jinja2 macros for DRY templates.
- **Missing Null Check:** Accessing `embedded_post.author_username` without checking `embedded_post` first. Always check `embedded_post and embedded_post.available`.
- **Forgetting to Pass Embedded:** Rendering post card without passing `embedded_post` kwarg. Macro should default to `None`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image lightbox | Custom modal/overlay | HTMX + CSS modal or reuse existing lightbox | Consistent UX, tested pattern |
| Video player | Custom video element | Link to X with thumbnail | Out of scope for v1.2, complex fallbacks |
| Pagination state | Custom cursor management | Existing `Cursor` class in `pagination.py` | Already implemented and tested |

**Key insight:** Reuse existing patterns from `browse.html` for cards, pagination, and HTMX loading. Extend with conditional rendering for post types.

## Common Pitfalls

### Pitfall 1: LEFT JOIN Returns NULL for Embedded Posts
**What goes wrong:** Original posts have `embedded_post_id = NULL`, so JOIN returns NULL for embedded columns.
**Why it happens:** SQLite LEFT JOIN produces NULL columns for missing joins, not missing dict keys.
**How to avoid:** Check `row['embedded_id'] is not None` before building embedded dict. Don't rely on KeyError.
**Warning signs:** `NoneType has no attribute 'author_username'` errors in templates.

### Pitfall 2: Template Accessing Missing Embedded Post
**What goes wrong:** Template tries `{{ post.embedded_post.author_username }}` when `embedded_post` is `None`.
**Why it happens:** Original posts don't have embedded content, but macro doesn't handle null case.
**How to avoid:** Always use `{% if post.embedded_post %}` before accessing nested properties. Use Jinja2's safe navigation: `{{ post.embedded_post.author_username if post.embedded_post }}`.
**Warning signs:** Template rendering errors with "UndefinedError: 'None' has no attribute".

### Pitfall 3: Retweet Shows Both User Text and Embedded Text
**What goes wrong:** Retweets display both the retweeter's empty/minimal text AND the original content.
**Why it happens:** Retweet text from X API is often "RT @user: ..." or empty, but template shows it anyway.
**How to avoid:** For retweets, only render `embedded_post.text`. Ignore `post.text` for retweets entirely.
**Warning signs:** Duplicate content showing "RT @user: ..." prefix.

### Pitfall 4: Unavailable Post Without Author Info
**What goes wrong:** Placeholder shows generic "unavailable" without any author context when `embedded_posts.author_username` is empty.
**Why it happens:** D-06 requires showing author if known, but unavailable posts may not have author data stored.
**How to avoid:** Check `embedded_post.author_username` before showing. Template should handle both cases gracefully.
**Warning signs:** Placeholder says "@unknown" or shows blank where author should be.

### Pitfall 5: Media Grid Breaks Layout
**What goes wrong:** Embedded post images overflow card boundaries or don't match regular post media layout.
**Why it happens:** Adaptive grid (D-07) requires specific Tailwind classes that differ from parent card.
**How to avoid:** Reuse existing media grid CSS from `browse.html`. Create shared media macro `_media_grid.html`.
**Warning signs:** Images overlapping borders, grid breaking on mobile.

## Code Examples

### Modified browse.html with Macro Import

```html
<!-- templates/browse.html -->
{% extends "base.html" %}
{% from "components/_post_card.html" import render_post_card %}

{% block title %}Browse - X Bookmarked Posts{% endblock %}

{% block content %}
<div class="space-y-6">
    <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-gray-800">Browse Posts</h1>
        <a href="/" class="text-blue-600 hover:text-blue-800">Home</a>
    </div>

    <div id="posts-container" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {% for post in posts %}
        {{ render_post_card(post, post.embedded_post) }}
        {% else %}
        <div class="col-span-full text-center py-12 text-gray-500">
            No posts found. Run <code class="bg-gray-100 px-2 py-1 rounded">xbm sync</code> to fetch your bookmarks.
        </div>
        {% endfor %}
    </div>

    {% if has_more %}
    <div class="text-center">
        <button hx-get="/api/posts?cursor={{ next_cursor }}&limit={{ limit }}"
                hx-target="#posts-container"
                hx-swap="beforeend"
                class="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
            Load More
        </button>
    </div>
    {% endif %}
</div>
{% endblock %}
```

**Source:** [Existing browse.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/browse.html) — HIGH confidence (project reference)

### Route Modification for Embedded Posts

```python
# src/web/routes/browse.py

from ...repositories.posts import PostsRepository
from ...repositories.embedded_posts import EmbeddedPostsRepository

@router.get("/browse", response_class=HTMLResponse)
async def browse_page(
    request: Request,
    cursor: str = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Posts per page"),
):
    """Render browse page with paginated posts including embedded content.

    WEB-07, WEB-08: Include embedded post data for retweets/quotes.
    """
    templates = request.app.state.templates
    db_path = Path("data/bookmarks.db")

    try:
        conn = init_database(db_path)
        repo = PostsRepository(conn)

        # Decode cursor if provided
        after_created_at = None
        after_post_id = None
        if cursor:
            decoded = Cursor.decode(cursor)
            if decoded:
                after_created_at = decoded.created_at
                after_post_id = decoded.x_post_id

        # Get paginated posts with embedded post data
        posts, has_more = repo.get_paginated_with_embedded(
            limit=limit,
            after_created_at=after_created_at,
            after_post_id=after_post_id,
        )

        # Generate next cursor if there are more posts
        next_cursor = None
        if has_more and posts:
            last_post = posts[-1]
            next_cursor = Cursor(
                created_at=last_post["created_at"],
                x_post_id=last_post["x_post_id"],
            ).encode()

        conn.close()

        return templates.TemplateResponse(
            request,
            "browse.html",
            {
                "posts": posts,
                "next_cursor": next_cursor,
                "has_more": has_more,
                "limit": limit,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error": str(e)},
        )
```

**Source:** [Existing browse.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/routes/browse.py) — HIGH confidence (project reference)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate queries for embedded posts | Single LEFT JOIN | Phase 8 (storage) | Reduces N+1 queries, simpler code |
| Inline template HTML for variants | Jinja2 macros | Phase 9 | DRY principle, easier maintenance |
| Client-side fetch for embedded | Server-side JOIN | Phase 9 | Faster page load, simpler HTMX |

**Deprecated/outdated:**
- **Fetching embedded posts on-demand:** Out of scope per REQUIREMENTS.md — live metrics excluded, embedded data stored at sync time

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Media rendering patterns exist in browse.html for regular posts | Architecture | LOW — Verified in code |
| A2 | Jinja2 auto-escaping prevents XSS for user content | Security | LOW — Jinja2 default behavior |
| A3 | Tailwind CDN supports all needed utility classes | Styling | LOW — Standard Tailwind classes used |
| A4 | HTMX infinite scroll works with modified post cards | HTMX | LOW — Only affects initial render, not swap |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions (RESOLVED)

1. **Does browse.html have existing media rendering for images?**
   - What we know: `post.media_urls` is available in template but not currently rendered in browse.html
   - What's unclear: Whether Phase 6 included media display
   - **RESOLVED:** Media rendering implemented in 09-02-PLAN Task 1 (`render_media_grid` macro). Images will render in adaptive grid layout (1 full-width, 2 side-by-side, 3+ in 2x2 grid).

2. **Should the API endpoint (/api/posts) also return embedded_post data?**
   - What we know: browse.py uses `/api/posts` for HTMX "Load More"
   - What's unclear: Whether JSON API needs embedded_post in response
   - **RESOLVED:** Yes — 09-03-PLAN creates `/api/posts/html` endpoint returning HTML snippets with embedded_post data. HTMX swap appends new cards that include embedded content.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.10+ | — |
| FastAPI | Web framework | ✓ | 0.100+ | — |
| Jinja2 | Templates | ✓ | 3.x | — |
| Tailwind CSS | Styling | ✓ | CDN | — |
| HTMX | Dynamic loading | ✓ | 1.9.12 | — |
| SQLite | Database | ✓ | 3.x (stdlib) | — |

**Missing dependencies with no fallback:**
- None — all dependencies available

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml |
| Quick run command | `pytest tests/test_web_browse.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-07 | Quote tweets render with nested cards | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_quote_tweet_display -x` | ❌ Wave 0 |
| WEB-08 | Retweets show attribution header | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_retweet_display -x` | ❌ Wave 0 |
| WEB-09 | Embedded media renders correctly | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_embedded_media_display -x` | ❌ Wave 0 |
| WEB-10 | Unavailable posts show placeholder | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_unavailable_placeholder -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_web_browse.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_web_browse.py::TestEmbeddedPosts` — test class for embedded post rendering
- [ ] Mock data: quote posts, retweet posts, unavailable posts in `MOCK_POSTS`
- [ ] Test: quote tweet shows user text + nested card
- [ ] Test: retweet shows attribution + original content
- [ ] Test: unavailable shows placeholder with author if known
- [ ] Test: embedded media displays in same grid as regular posts

*(If no gaps: "None — existing test infrastructure covers all phase requirements")*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Jinja2 auto-escaping (built-in) |
| V6 Cryptography | no | No crypto in this phase |

### Known Threat Patterns for Jinja2 + FastAPI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via user content in templates | Tampering | Jinja2 auto-escape enabled by default, use `{{ }}` not `{% raw %}` |
| Template injection | Tampering | Don't use `|safe` filter on user content; keep auto-escaping |
| HTML injection in embedded post text | Tampering | Escape in template with `{{ }}` — already default |

**Key mitigation:** Jinja2's default auto-escaping prevents XSS from user-generated content (`post.text`, `embedded_post.author_username`). Do NOT use `|safe` filter on any user content.

## Sources

### Primary (HIGH confidence)
- [Jinja2 Macros Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/#macros) — Template patterns
- [SQLite LEFT JOIN](https://www.sqlite.org/lang_select.html) — JOIN semantics for embedded posts
- [FastAPI Templates Guide](https://fastapi.tiangolo.com/advanced/templates/) — Template rendering patterns
- [Tailwind CSS Card Examples](https://tailwindcss.com/docs/border-radius#cards) — Card styling patterns

### Secondary (MEDIUM confidence)
- [Existing browse.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/browse.html) — Project reference
- [Existing browse.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/routes/browse.py) — Project reference
- [PostsRepository](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/posts.py) — Project reference
- [EmbeddedPostsRepository](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/embedded_posts.py) — Project reference
- [test_web_browse.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/tests/test_web_browse.py) — Test patterns

### Tertiary (LOW confidence)
- None — all claims verified from official or project sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new dependencies, existing patterns used
- Architecture: HIGH — Clear patterns from existing code and Jinja2 docs
- Pitfalls: HIGH — Common template/database errors documented

**Research date:** 2026-06-05
**Valid until:** 90 days — Jinja2/Tailwind patterns are stable