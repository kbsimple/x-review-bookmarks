# Phase 9: Web Display - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Render retweets and quote tweets with full original content in the web interface. Users see nested cards for quote tweets (their commentary above the quoted post) and clear "Reposted from @user" attribution for retweets. Unavailable originals show a placeholder. Media (images, videos) from embedded posts render with the same patterns as regular posts.

This phase delivers:
- Quote tweet cards with nested original post display
- Retweet cards with clear attribution headers
- Embedded post media rendering (images, videos)
- Unavailable post placeholder handling
- Data fetching to join posts with embedded_posts

**Out of scope (Phase 10+):**
- CLI rendering of embedded posts (Phase 10)
- Cast receiver display of embedded posts (Phase 11)
- FTS5 search including embedded post text (future)
- Live retweet counts (out of scope)

</domain>

<decisions>
## Implementation Decisions

### Quote Tweet Layout
- **D-01:** Nested card layout for quote tweets.
  - Outer card: User's quote commentary (text, author, date)
  - Inner card: Original post with gray-50 background and gray-200 border
  - Rationale: Clear visual hierarchy separating user's commentary from quoted content.

- **D-02:** Quote attribution shown as gray "Quoting @username" label above nested card.
  - Label outside the nested card, not inside
  - Rationale: Signals relationship without competing with original author display.

### Retweet Display
- **D-03:** Header line shows "Reposted from @original_author" in gray text.
  - Original content displays below the header (same layout as original posts)
  - Rationale: Clear attribution, minimal visual complexity.

- **D-04:** Retweeter info visible above header.
  - Smaller text: "Reposted by @retweeter"
  - Shows who retweeted while keeping original author prominent
  - Rationale: Full context for why this post appeared in bookmarks.

### Unavailable Handling
- **D-05:** Gray placeholder card for unavailable embedded posts.
  - Text: "Original post unavailable"
  - Generic post icon (document/X logo)
  - Gray background matching nested card style
  - Rationale: Graceful degradation without breaking the feed.

- **D-06:** Show author if known from reference ID.
  - If `embedded_posts.author_username` exists but `available=false`: show "@username" in gray
  - Rationale: Partial information is better than none.

### Media Rendering
- **D-07:** Adaptive grid layout for embedded images.
  - 1 image: full-width
  - 2 images: side-by-side
  - 3+ images: 2x2 grid (max 4 visible, same as X)
  - Rationale: Matches regular post card behavior, familiar to users.

- **D-08:** Click-to-expand lightbox for images.
  - Full-size image overlay with close button
  - Same behavior as regular post cards
  - Rationale: Consistent pattern, allows viewing full image.

- **D-09:** Video thumbnail with play icon overlay.
  - If `preview_image_url` available from X API: show thumbnail
  - Click opens X in new tab
  - Fallback: Generic video icon if no thumbnail
  - Rationale: Visual preview without complex video player implementation.

### Claude's Discretion
- Exact Tailwind CSS class names for nested cards
- Animation timing for hover effects
- Responsive breakpoints for mobile vs desktop
- Loading states while fetching embedded posts
- Error handling for failed embedded post fetches

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — WEB-07, WEB-08, WEB-09, WEB-10 (Web display requirements for Phase 9)
- `.planning/REQUIREMENTS.md` §Out of Scope — Live metrics, recursive quotes, thread context

### Prior Phase Context
- `.planning/phases/08-storage-foundation/08-CONTEXT.md` — Storage decisions, embedded_posts table structure
- `.planning/phases/06-web-foundation/06-CONTEXT.md` — Web framework decisions, template patterns
- `.planning/phases/07-cast-integration/07-CONTEXT.md` — Cast button integration, receiver patterns

### Existing Code (from prior phases)
- `src/web/templates/browse.html` — Existing post card layout, grid structure, HTMX infinite scroll
- `src/web/templates/base.html` — Base template with navigation, Tailwind, HTMX includes
- `src/web/routes/browse.py` — Post pagination endpoint, PostsRepository usage
- `src/repositories/posts.py` — `_row_to_dict()` returns `post_type` and `embedded_post_id`
- `src/repositories/embedded_posts.py` — `get_by_id()` for fetching embedded post data

### Architecture
- `CLAUDE.md` — Technology stack (FastAPI, Jinja2, Tailwind, HTMX)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **src/web/templates/browse.html** — Post card grid pattern (`grid gap-4 md:grid-cols-2 lg:grid-cols-3`)
- **src/web/templates/browse.html** — Individual card structure (`bg-white rounded-lg shadow p-4 hover:shadow-md`)
- **src/web/templates/base.html** — Navigation, Tailwind CDN, HTMX CDN
- **src/repositories/posts.py** — `get_paginated()` returns posts with `post_type` and `embedded_post_id`
- **src/repositories/embedded_posts.py** — `get_by_id()` fetches embedded post data

### Established Patterns
- **Post cards:** White background, rounded corners, shadow, hover effect
- **Grid layout:** `grid gap-4 md:grid-cols-2 lg:grid-cols-3`
- **Author display:** `@username` in gray text, date in smaller gray
- **Link styling:** `text-blue-500 hover:text-blue-700`
- **Note styling:** `bg-yellow-50 border-l-2 border-yellow-400`

### Integration Points
- **Template:** Modify `browse.html` to conditionally render post cards based on `post_type`
- **Route:** `browse.py` needs to fetch embedded post data for retweets/quotes
- **Repository:** Create `get_embedded_post()` call in browse route or template filter
- **Component:** Consider `_post_card.html` partial for reuse (original, retweet, quote variants)

</code_context>

<specifics>
## Specific Ideas

- Quote tweet card: user's text on top, "Quoting @username" label, nested gray card below
- Retweet card: "Reposted by @retweeter" small line, "Reposted from @author" header, original content
- Unavailable: gray placeholder card with "Original post unavailable" and @username if known
- Media in nested cards: same adaptive grid as parent post
- Loading state: skeleton or spinner while fetching embedded post data

</specifics>

<deferred>
## Deferred Ideas

- FTS5 search including embedded post text (SRCH-F01) — future phase
- Display original post metrics on retweets (MET-F01) — future phase
- Quote-of-quote chain support beyond 1 level (REC-F01) — out of scope
- Interactive video player in web app — out of scope for v1.2

</deferred>

---
*Phase: 09-web-display*
*Context gathered: 2026-06-05*