# Phase 16: Viewer Presentation Modes - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two presentation modes to the static viewer (`index.html` in `src/services/static_export.py`):

- **Stream mode** — the existing scrollable vertical list (default, unchanged)
- **Carousel mode** — shows one post at a time, prominently, with prev/next navigation and keyboard arrow key support

A mode switcher in the header lets users toggle between modes. Active mode persists via localStorage. Both modes work with oEmbed rich embeds.

No changes to Python, CLI, or data model — this is pure viewer JS/CSS.

</domain>

<decisions>
## Implementation Decisions

### Mode Switcher UX
- Segmented pill control: two adjacent buttons `[Stream] [Carousel]` — active button filled with `--color-accent`
- Label text: "Stream" / "Carousel" (matches ROADMAP language)
- Placement: right side of `#header`, after count badge
- Stream is always the default on page load (localStorage overrides if user previously switched)

### Carousel Layout
- Card max-width: `860px` (wider than stream's 720px), centered — more breathing room for single-post focus
- Navigation controls: centered below the post — `← Prev` | `3 / 47 posts` | `Next →`
- Post counter shown between prev/next buttons; header count badge shows total filtered count as normal
- Auto-scroll to `window.scrollTo(0, 0)` on each prev/next navigation

### State Persistence
- Active mode saved to `localStorage` key `xbm_mode` — persists across page reloads
- Carousel index resets to 0 on any filter/search change (avoids out-of-bounds on shrinking result sets)
- Stream scroll position (`window.scrollY`) is saved when switching to carousel and restored when switching back

### Keyboard Navigation
- Left/Right arrow keys only — standard carousel convention; Up/Down reserved for page scroll
- Global `keydown` listener on `document` — no focus requirement
- Escape key switches back to Stream mode
- No wrap-around: Next disabled at last post, Prev disabled at first post

### Claude's Discretion
- Exact CSS for disabled button state (opacity, cursor)
- Animation/transition on mode switch (subtle fade or none)
- Whether controls row (`#controls`) stays visible in carousel mode or is hidden

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `renderPost(post, reviewState)` — existing function handles all post types including oEmbed; reuse unchanged in carousel
- `filterAndSort()` — existing function returns ordered results array; carousel indexes into this array
- `allPosts`, `searchIndex`, `reviewMap`, `totalPostCount` — existing global state; carousel reads from these
- CSS variables (`--color-accent`, `--color-card`, `--color-border`, etc.) — use throughout for consistency
- `esc()` helper — use for any dynamic string in new HTML

### Established Patterns
- All rendering is DOM-manipulation via `innerHTML` assignment — match this pattern for carousel
- `renderView()` is the central render orchestrator — extend it with a mode branch
- Event listeners wired directly to DOM elements after page load — add keyboard listener the same way
- `loadTwitterWidget()` + `window.twttr.widgets.load()` call pattern for oEmbed — must be called after carousel renders oEmbed posts too

### Integration Points
- `#header` — add mode switcher buttons here (after count badge span)
- `renderView()` — branch on active mode: stream path (existing), carousel path (new)
- Search/filter/sort event listeners already call `renderView()` — carousel index reset happens inside `renderView()` when mode is carousel
- `_build_index_html()` in `src/services/static_export.py` — all changes are inside this method's returned string

</code_context>

<specifics>
## Specific Ideas

- Carousel prev/next buttons should use `←` / `→` or `‹` / `›` Unicode arrows — keep it minimal, matching existing link style
- Disabled button state: `opacity: 0.3; cursor: not-allowed; pointer-events: none`
- oEmbed posts in carousel: call `loadTwitterWidget()` + `twttr.widgets.load(cardEl)` after inserting carousel card DOM

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
