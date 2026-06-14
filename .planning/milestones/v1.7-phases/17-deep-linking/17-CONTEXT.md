# Phase 17: Deep Linking — Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the ability to share a direct URL to any specific post in the static Netlify viewer.
A "share" icon on each card copies a `#post-{id}` hash URL to the clipboard.
Opening that URL opens the viewer in a focused single-post carousel view with filters cleared
and an "XBM Home" button in the header to return to the full viewer.

This is a pure client-side, static-site feature — no server changes.

</domain>

<decisions>
## Implementation Decisions

### Deep Link Entry Experience
- **D-01:** Opening a deep link URL (`#post-{x_post_id}`) puts the viewer into **carousel mode** showing only that specific post. All filters (search, date, sort) are cleared.
- **D-02:** The viewer detects the hash on page load (`window.location.hash`) and navigates to the matching post after data has loaded.
- **D-03:** If the hash references a post ID not found in `allPosts` (e.g. stale link, post removed from export), show a graceful "Post not found" message with an "XBM Home" link.

### URL Scheme
- **D-04:** Hash format: `#post-{x_post_id}` — e.g. `https://xbm-viewer-export.netlify.app/#post-1784230491234`. The `post-` prefix keeps the hash self-documenting and avoids collisions with future hash uses.
- **D-05:** The URL bar does **not** auto-update as the user navigates carousel in normal (non-deep-link) mode. The hash only appears when the user explicitly copies a share link.

### Share Icon UX
- **D-06:** A share icon (📤 — standard native share icon, or a link-chain icon as fallback) appears on every post card.
- **D-07:** Clicking the icon copies the deep link URL to the clipboard via `navigator.clipboard.writeText()`. A brief visual confirmation (icon changes, or a small "Copied!" toast) acknowledges the copy.
- **D-08:** The share icon is visible in both carousel mode and stream mode.

### "XBM Home" Navigation
- **D-09:** When the viewer is in deep-link mode (arrived via `#post-{id}`), the header shows an **"XBM Home"** button replacing the Carousel/Stream mode switcher.
- **D-10:** Clicking "XBM Home" navigates to the root URL (clears the hash), resetting the viewer to its default state — no filters, full post list, user's persisted mode (carousel/stream).
- **D-11:** "XBM Home" does **not** say "Back to all posts" — the user may not have come from all posts.

### Filter Interaction
- **D-12:** Deep link arrival unconditionally clears all filters and bypasses filter/sort state. The linked post is always shown regardless of what filters might have been active.
- **D-13:** No filter state is encoded in the deep link URL — links are deliberately minimal (post ID only).

### Claude's Discretion
- Visual style of the share icon and "Copied!" confirmation — match the existing card footer style (small, muted, consistent with "View on X" link).
- Exact animation/duration of copy confirmation feedback.
- Whether the deep-link mode adds a visible "Linked post" label to the card header.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Viewer Implementation
- `src/services/static_export.py` — entire viewer lives in `_build_index_html()`. All CSS/HTML/JS is an inline Python string. No bundler, no templates.

### Existing Card Footer Pattern
- `src/services/static_export.py` — `renderCardFooter()` function (search for `function renderCardFooter`) — share icon should match the visual style of the "View on X" link already there.

### Test Pattern
- `tests/test_static_export_service.py` — `TestIndexHtmlCarousel` class shows the string-grep test pattern used for all viewer features. New deep-link tests follow the same pattern.

### No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `allPosts` (object): keyed by `x_post_id` — direct lookup by post ID is O(1), no search needed for deep link resolution.
- `searchIndex` (array): each entry has `.id` field matching `x_post_id`. Used to find carousel index for a given post ID.
- `renderCarousel(results, idx)`: renders single-post carousel view — deep link can reuse this directly with a single-item results array or by finding the matching index in the full unfiltered list.
- `renderCardFooter(post)`: existing footer pattern — share icon slots in here alongside "View on X".
- `renderView()`: entry point for all rendering — deep-link init can call `renderView()` after setting `carouselIndex` to the target post.

### Established Patterns
- All viewer JS is inline in the Python string constant. No ES modules, no bundler.
- `esc()` helper used for all user content in innerHTML — post IDs embedded in URLs must go through `esc()`.
- `localStorage.getItem('xbm_mode')` persists mode — deep link arrival should override but not overwrite this (so returning home restores the user's preferred mode).
- Bootstrap: data is loaded via `Promise.all([fetch(...)])` — deep link detection should run inside the `.then()` handler after data is available.

### Integration Points
- `renderCardFooter()` — share icon button added here; `post.x_post_id` already available.
- `window.location.hash` read on bootstrap (inside `.then()` after JSON loads).
- `setMode()` / `renderView()` — deep link arrival calls these after clearing filters.
- `#header` HTML — "XBM Home" button conditionally replaces `.mode-switcher` when in deep-link mode; needs a JS flag (`let deepLinkMode = false`) and a CSS class on `<body>` (e.g. `body.deep-link-mode`).

</code_context>

<specifics>
## Specific Ideas

- User was specific: the home link says "**XBM Home**" — not "Back", not "All posts".
- User was specific: standard share icon (📤) — not a text label like "Copy link".
- The focused view should not feel like an error state — it's a valid, intentional entry point.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-deep-linking*
*Context gathered: 2026-06-14*
