# Phase 18: Background Prefetch - Context

**Gathered:** 2026-07-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a forward-weighted prefetch pool to carousel mode: pre-render a window of posts (5 ahead, 2 behind)
into hidden DOM nodes and pre-initialize Twitter widgets via `twttr.widgets.load()` before the user
navigates to them. On navigation, swap the pre-rendered node instead of re-rendering from scratch.

Carousel-only. Stream mode is out of scope (posts are already all in DOM). No new CLI or Python changes.

</domain>

<decisions>
## Implementation Decisions

### Pool Data Structure
- **D-01:** `prefetchPool = new Map()` — `postId → HTMLElement` (the pre-rendered `.post-card` DOM node). O(1) lookup on navigation, easy enumeration for eviction.

### Prefetch Window
- **D-02:** `PREFETCH_AHEAD = 5`, `PREFETCH_BEHIND = 2` — forward-weighted as user decided. Total window ≤ 7 nodes in pool at any time.

### Hidden Prefetch Container
- **D-03:** A single `div#prefetch-container` appended to `<body>`, styled `position:absolute; left:-9999px; top:-9999px; width:500px; visibility:hidden; pointer-events:none;`. Pre-rendered card nodes live here while warming. Twitter's `twttr.widgets.load()` requires elements to be in the DOM — a detached element won't work.

### Trigger Timing
- **D-04:** After `renderCarousel()` completes, call `schedulePrefetch(results, idx)`. This uses `requestIdleCallback(cb, {timeout:200})` when available, falling back to `setTimeout(cb, 200)`. The 200ms max ensures prefetch starts quickly even on busy pages. Cancel the previous timer before scheduling a new one to avoid stacked prefetch jobs on rapid navigation.

### Widget Warming
- **D-05:** Call `twttr.widgets.load(prefetchContainer)` directly (not `loadTwitterWidget()`). Reason: `loadTwitterWidget()` calls `document.querySelectorAll('.oembed-container').forEach(_setupSkeletonFallback)`, which would set up 5-second fallback timers for hidden prefetch elements — wasteful timer pollution. Warming the prefetch container directly skips skeleton setup.
- **D-06:** If `window.twttr && window.twttr.widgets` is not ready when `_runPrefetch` runs, skip widget warming for this batch. The nodes are still stored in the pool (DOM node reuse still helps). When the user navigates to such a post, the warm-state check detects the unwarmed state and falls through to `loadTwitterWidget()`.

### Node Reuse on Navigation
- **D-07:** In `renderCarousel(results, idx)`, check `prefetchPool.has(entry.id)` before generating card HTML.
  - **Pool hit:** Retrieve the pre-rendered node, delete it from the pool, then rebuild the container using explicit DOM insertion: capture `topNavNode = t.children[0]` and `navNode = t.children[1]` from a temp div, clear `#post-list.innerHTML = ''`, append `topNavNode`, the card node, then `navNode`. Re-attach event listeners as usual (they find elements by ID, still works).
  - **Pool miss:** Fall back to existing `container.innerHTML = topNav + cardHtml + nav` path (zero regression).

### Warm-State Detection After Node Swap
- **D-08:** After inserting a pool node, check `post.oembed_html && !cardNode.querySelector('blockquote.twitter-tweet')`.
  - If blockquote is gone → widget is an iframe → already warmed → skip `loadTwitterWidget()`.
  - If blockquote still present → twttr wasn't ready when prefetched → call `loadTwitterWidget()` (current behavior, no regression).

### Pool Invalidation
- **D-09:** Call `clearPrefetchPool()` at the start of the carousel branch in `renderView()` (before `renderCarousel()`). `renderView()` is called when filters/search/sort change — clearing the pool ensures stale pre-rendered nodes (built for the old result set) are not used for the new result set. Direct navigation calls `renderCarousel()` directly (not through `renderView()`), so the pool is NOT cleared on swipe/click/keyboard — that's intentional (pool reuse is the entire point).

### `clearPrefetchPool()`
- **D-10:** Remove all pool nodes from `#prefetch-container` (`.remove()` on each), clear the Map. Also cancel any pending prefetch timer.

### Prefetch Scope
- **D-11:** Prefetch all post types (oEmbed, original, retweet, quote). For non-oEmbed posts, pre-rendered DOM node reuse avoids HTML string parsing and DOM construction on navigation. For oEmbed posts, it additionally pre-warms the Twitter widget. Consistent, simple code.

### Claude's Discretion
- `_getPrefetchContainer()` — lazy-init function that creates the container on first call and caches it in `_prefetchContainer` variable
- `_prefetchTimerId` — tracks the pending requestIdleCallback/setTimeout id for cancellation
- New global variables: `PREFETCH_AHEAD`, `PREFETCH_BEHIND`, `prefetchPool`, `_prefetchContainer`, `_prefetchTimerId`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Implementation File
- `src/services/static_export.py` — All JS lives inline in this file as a Python string. Key sections:
  - Line ~777: Global state block (add new prefetch globals here)
  - Line ~1035: `renderOEmbedCard()` — generates `.post-card` with `.oembed-container` and `.tweet-skeleton`
  - Line ~1049: `renderPost()` — dispatcher to card type renderers
  - Line ~1004: `loadTwitterWidget()` — loads Twitter CDN script, calls `twttr.widgets.load(#post-list)`
  - Line ~974: `_onWidgetRendered()` and `_setupSkeletonFallback()` — widget lifecycle callbacks
  - Line ~1083: `renderCarousel()` — the function to modify for pool hit/miss
  - Line ~1163: `renderView()` — add `clearPrefetchPool()` before `renderCarousel()` call in carousel branch

### Requirements
- `.planning/REQUIREMENTS.md` — PREFETCH-01 through PREFETCH-08

### Phase Roadmap Entry
- `.planning/ROADMAP.md` — Phase 18: Background Prefetch, success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `renderPost(post, rs)` — returns HTML string; wrap in `document.createElement('div').innerHTML = …` to get a DOM node for the pool
- `allPosts` — global Map, available in prefetch worker; no need to pass as argument
- `reviewMap` — global Map, same
- `twttr.widgets.load(element)` — existing pattern; used in `loadTwitterWidget()`, safe to call with any element

### Established Patterns
- All JS is inline in `static_export.py` as a Python triple-quoted string — new functions go in the same block
- `let`/`const` for variables, `function` declarations for functions
- Event listeners attached by ID after innerHTML set (same pattern will work after DOM node swap)
- `document.querySelectorAll('.oembed-container').forEach(...)` is the existing pattern for iterating oEmbed containers — avoid calling this for prefetch containers (use direct reference instead)

### Integration Points
- `renderCarousel(results, idx)` — modify to check pool and use DOM node swap path
- `renderView()` — add `clearPrefetchPool()` before the `renderCarousel()` call in carousel branch
- After `renderCarousel()` sets up event listeners, add `schedulePrefetch(results, idx)` at the end
- Global state block (line ~777) — add `prefetchPool`, `_prefetchContainer`, `_prefetchTimerId`, `PREFETCH_AHEAD`, `PREFETCH_BEHIND`

### Key Constraint
- `twttr.widgets.load()` requires the target element to be in the DOM (not detached). The `#prefetch-container` must be appended to `document.body` before calling `twttr.widgets.load(container)`.

</code_context>

<specifics>
## Specific Ideas

- The `width:500px` on `#prefetch-container` ensures Twitter widget renders at a sensible width (mirrors typical post card width). Too narrow or zero-width may prevent widget rendering.
- Cancel the pending prefetch timer on rapid navigation: `cancelIdleCallback(_prefetchTimerId)` / `clearTimeout(_prefetchTimerId)` before scheduling the new one.
- On `clearPrefetchPool()`, also cancel pending timer — avoids a stale prefetch job running after the result set changes.

</specifics>

<deferred>
## Deferred Ideas

- Configurable prefetch window size via viewer UI setting — future milestone
- Service Worker pre-caching of posts.json/search-index.json across page reloads — future milestone
- Prefetch in stream mode — no use case (all posts already in DOM)
- IndexedDB persistence of pre-warmed widget state across sessions — premature

</deferred>

---

*Phase: 18-background-prefetch*
*Context gathered: 2026-07-18*
