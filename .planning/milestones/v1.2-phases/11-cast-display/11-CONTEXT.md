# Phase 11: Cast Display - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Display embedded posts (retweets and quote tweets) on TV via Google Cast with TV-optimized visual styling. Users see nested cards for quote tweets, clear attribution headers for retweets, and graceful unavailable placeholders — all with larger text, higher contrast, and TV-friendly layouts.

This phase delivers:
- Quote tweet cards with TV-optimized nested layout
- Retweet cards with "Reposted from" attribution on TV
- Embedded post media rendering (full-width for TV)
- Unavailable post placeholder for Cast receiver
- Message passing for embedded post data

**Out of scope:**
- Queue management (play next, shuffle) — future enhancement
- Voice control via Google Assistant — out of scope
- CLI or Web display changes (Phases 9-10 already complete)

</domain>

<decisions>
## Implementation Decisions

### TV Typography (Per CAST-06)
- **D-01:** Base text size 3rem for TV readability (vs 2rem web default).
  - Quote text, post content: 3rem with 1.5 line-height
  - Author names: 2.5rem (maintain hierarchy)
  - Attribution labels ("Quoting", "Reposted from"): 1.8rem
  - Rationale: TV viewing distance requires 50% larger text than desktop.

- **D-02:** High contrast color scheme for TV.
  - Background: #000 (pure black) — matches existing receiver
  - Primary text: #fff (white) — maximum contrast
  - Secondary text: #888 (gray) — readable but subordinate
  - Embedded card background: #1a1a1a — distinct but not harsh
  - Nested card border: #333 — subtle separation
  - Rationale: TVs have varying contrast capabilities; pure contrast is safest.

### Quote Tweet Layout (Per CAST-06, CAST-07)
- **D-03:** Nested card structure matches Phase 9 pattern, TV-optimized.
  - Outer card: User's quote commentary with white text on black
  - "Quoting @username" label in gray above nested card
  - Inner card: Original post with #1a1a1a background, #333 border
  - Vertical spacing: 3rem gap between user commentary and quoted card
  - Rationale: Same nested structure as web, with TV-appropriate spacing and contrast.

- **D-04:** Author info prominent on TV.
  - Avatar: 80px circle (same as existing post display)
  - Author name: 2.5rem bold (same as existing)
  - Quoted author name: 2rem bold (slightly smaller hierarchy)
  - Rationale: TV screens allow larger author display without crowding.

### Media Display (Per CAST-06)
- **D-05:** Full-width media for embedded posts on TV.
  - Single image: max-width 100%, centered
  - Multiple images: vertical stack with 1rem gap (no grid on TV — vertical scroll)
  - Video thumbnails: Same as images, click-to-play placeholder
  - Rationale: TV screens favor vertical content flow; side-by-side images too small for TV.

- **D-06:** Media from embedded posts displayed within nested card.
  - Embedded post images render in the inner card (quoted content)
  - Combined media from both quoter and quoted (per D-08 in Phase 9)
  - Rationale: Media belongs with its associated post content.

### Retweet Display (Per CAST-07)
- **D-07:** Retweet header matches Phase 9 pattern, TV-optimized.
  - "Reposted by @retweeter" in 1.5rem gray text (top line)
  - "Reposted from @original_author" in 1.8rem gray text (header line)
  - Original author displayed with same prominence as original posts
  - Rationale: Clear attribution hierarchy, same pattern as web.

- **D-08:** Retweet content displays with same styling as original posts.
  - Same text sizes, same author prominence
  - Media displayed full-width within retweet card
  - Rationale: Consistency with existing post display, TV-optimized.

### Unavailable Handling (Per CAST-08)
- **D-09:** TV-friendly unavailable placeholder.
  - Gray background card (#1a1a1a) with centered message
  - "Original post unavailable" in 2rem gray text
  - Post icon (document/X logo) in 4rem gray
  - If author known: "@username" shown above message
  - Rationale: Graceful degradation with clear visual feedback on TV.

- **D-10:** Quote tweets with unavailable embedded posts.
  - Show quoter's commentary in normal post card
  - Show unavailable placeholder for the quoted content
  - Visual separation with 2rem gap
  - Rationale: User's commentary still visible, original unavailable clearly marked.

### Claude's Discretion
- Exact pixel values for TV spacing (padding, margins)
- Animation timing for loading states
- Error message wording for unavailable posts
- Fallback image for posts without media

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — CAST-06, CAST-07, CAST-08 (Cast display requirements for Phase 11)
- `.planning/REQUIREMENTS.md` §Out of Scope — Queue management, voice control

### Prior Phase Context
- `.planning/phases/09-web-display/09-CONTEXT.md` — Web display decisions (D-01 through D-09 for nested cards, attribution, unavailable handling)
- `.planning/phases/10-cli-display/10-CONTEXT.md` — CLI display decisions (same display concepts for different surface)
- `.planning/phases/07-cast-integration/07-CONTEXT.md` — Cast SDK integration, receiver patterns, message passing

### Existing Code
- `src/web/templates/receiver.html` — Current Cast receiver HTML/CSS (single post display)
- `src/web/static/js/cast.js` — Cast sender JavaScript (message passing)
- `src/web/routes/browse.py` — Post pagination endpoint
- `src/repositories/posts.py` — Post data with `post_type` and `embedded_post_id`
- `src/repositories/embedded_posts.py` — Embedded post data retrieval

### Architecture
- `CLAUDE.md` — Technology stack (FastAPI, Jinja2, Cast SDK)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **receiver.html** — Post display template with author, content, images, topics
- **cast.js** — CastManager class for session management and message passing
- **PostsRepository.get_paginated()** — Returns posts with `post_type` and `embedded_post_id`
- **EmbeddedPostsRepository.get_by_id()** — Fetches embedded post data

### Established Patterns
- **Receiver HTML structure:** Container > loading spinner, post-container (author, content, images, topics)
- **Cast message passing:** Custom namespace `urn:x-cast:com.bookmarked.posts` with LOAD_POST message
- **Post data format:** `{author_username, author_display_name, text, created_at, media_urls, topics}`
- **TV styling:** Black background, white text, large fonts (3rem base)

### Integration Points
- **Template:** Modify `receiver.html` to handle `post_type` (original, retweet, quote)
- **JavaScript:** Extend `loadPost()` to process `embedded_post` data
- **Repository:** Fetch embedded post data when `embedded_post_id` is present
- **CSS:** Add nested card styles for quote tweets, retweet headers, unavailable placeholders

</code_context>

<specifics>
## Specific Ideas

- Quote tweet: outer card with user's text, gray "Quoting @username" label, nested #1a1a1a card with original
- Retweet: "Reposted by @retweeter" small line, "Reposted from @author" header, original content
- Unavailable: #1a1a1a card with "Original post unavailable" and gray post icon
- Media in nested cards: full-width, vertical stack for TV
- Author info: same prominence as existing post display (80px avatar, 2.5rem name)

</specifics>

<deferred>
## Deferred Ideas

- Queue management for cast sessions (play next, shuffle) — future enhancement
- Voice control via Google Assistant — out of scope
- Interactive video player on TV — out of scope for v1.2
- Like/bookmark from TV — out of scope

</deferred>

---
*Phase: 11-cast-display*
*Context gathered: 2026-06-07*