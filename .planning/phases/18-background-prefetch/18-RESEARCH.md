# Phase 18: Background Prefetch - Research

**Researched:** 2026-07-18
**Domain:** Client-side JavaScript — carousel prefetch pool, requestIdleCallback, Twitter widget pre-initialization
**Confidence:** HIGH (all decisions locked in CONTEXT.md; codebase is the authoritative source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `prefetchPool = new Map()` — `postId → HTMLElement`
- **D-02:** `PREFETCH_AHEAD = 5`, `PREFETCH_BEHIND = 2`
- **D-03:** Single `div#prefetch-container` appended to `<body>`, styled `position:absolute; left:-9999px; top:-9999px; width:500px; visibility:hidden; pointer-events:none;`. Required because `twttr.widgets.load()` needs elements in the DOM.
- **D-04:** After `renderCarousel()` completes, call `schedulePrefetch(results, idx)` using `requestIdleCallback(cb, {timeout:200})` with `setTimeout(cb, 200)` fallback. Cancel previous timer before scheduling.
- **D-05:** Call `twttr.widgets.load(prefetchContainer)` directly (NOT via `loadTwitterWidget()`) to avoid triggering `_setupSkeletonFallback` timers on hidden elements.
- **D-06:** If `window.twttr && window.twttr.widgets` is not ready, skip widget warming — store node in pool anyway. Navigation falls through to `loadTwitterWidget()` on warm-state miss.
- **D-07:** Pool hit path in `renderCarousel`: retrieve node, delete from pool, rebuild container via explicit DOM insertion (not innerHTML). Pool miss: fall back to existing innerHTML path.
- **D-08:** Warm-state detection: `post.oembed_html && !cardNode.querySelector('blockquote.twitter-tweet')` — if blockquote gone, widget already warmed; skip `loadTwitterWidget()`.
- **D-09:** `clearPrefetchPool()` called at start of carousel branch in `renderView()`, before `renderCarousel()`. NOT cleared on direct `renderCarousel()` calls (navigation reuses pool).
- **D-10:** `clearPrefetchPool()` removes all pool nodes from `#prefetch-container`, clears the Map, cancels pending timer.
- **D-11:** Prefetch all post types (oEmbed, original, retweet, quote).

### Claude's Discretion

- `_getPrefetchContainer()` — lazy-init function, creates container on first call, caches in `_prefetchContainer` variable
- `_prefetchTimerId` — tracks pending requestIdleCallback/setTimeout id for cancellation
- New globals: `PREFETCH_AHEAD`, `PREFETCH_BEHIND`, `prefetchPool`, `_prefetchContainer`, `_prefetchTimerId`

### Deferred Ideas (OUT OF SCOPE)

- Configurable prefetch window size via viewer UI setting
- Service Worker pre-caching of posts.json/search-index.json across page reloads
- Prefetch in stream mode
- IndexedDB persistence of pre-warmed widget state across sessions

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PREFETCH-01 | Carousel pre-renders next 5 posts into DOM elements after current post renders | `schedulePrefetch` + `_runPrefetch` creates nodes via `renderPost()` + `document.createElement` |
| PREFETCH-02 | Carousel pre-renders previous 2 posts into DOM elements | Same `_runPrefetch`; window = `[idx - PREFETCH_BEHIND, idx + PREFETCH_AHEAD]` |
| PREFETCH-03 | Twitter widgets pre-initialized via `twttr.widgets.load()` on prefetched oEmbed posts | Direct call `twttr.widgets.load(prefetchContainer)` in `_runPrefetch` after inserting nodes |
| PREFETCH-04 | Prefetch scheduling uses `requestIdleCallback` with 200ms max timeout | `schedulePrefetch` wrapper with `typeof requestIdleCallback !== 'undefined'` guard |
| PREFETCH-05 | On navigation, swap pre-rendered node from pool when available | Pool-hit branch in `renderCarousel`; explicit DOM insertion, then warm-state check |
| PREFETCH-06 | Pool cleared and rebuilt when search/filter/sort changes result set | `clearPrefetchPool()` in `renderView()` carousel branch before `renderCarousel()` |
| PREFETCH-07 | Pool entries outside active window evicted as user navigates | `_runPrefetch` evicts entries not in new window after each navigation; pool bounded to ≤7 |
| PREFETCH-08 | String-grep tests verify `schedulePrefetch` and `prefetchPool` identifiers in generated HTML | New `TestIndexHtmlPrefetch` class in `tests/test_static_export_service.py` |

</phase_requirements>

---

## Summary

Phase 18 adds a forward-weighted prefetch pool to carousel mode. The implementation is entirely within the inline JavaScript block of `src/services/static_export.py` — no Python changes needed. There is no external library to research; the work is integrating three browser APIs (requestIdleCallback, DOM manipulation, twttr.widgets) with established patterns already present in the codebase.

All major design decisions are locked in CONTEXT.md. The key engineering complexity is: (1) correctly identifying the two navigation paths (direct `renderCarousel` vs. `renderView`-initiated) so the pool is cleared only when the result set changes, and (2) performing DOM insertion safely when swapping a pool node without triggering skeleton-fallback timer pollution.

The test requirement (PREFETCH-08) follows the established string-grep pattern used throughout `TestIndexHtmlCarousel` and `TestIndexHtmlDeepLink` — add a new `TestIndexHtmlPrefetch` class that generates `index.html` and asserts specific identifier strings are present.

**Primary recommendation:** Implement as four additions to the inline JS: (1) new globals block, (2) `_getPrefetchContainer` + `clearPrefetchPool` + `schedulePrefetch` + `_runPrefetch` functions, (3) modified `renderCarousel` (pool hit/miss + `schedulePrefetch` call at end), (4) `clearPrefetchPool()` inserted in `renderView` carousel branch.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Prefetch pool management | Browser / Client (inline JS) | — | All viewer logic is client-side; no server |
| requestIdleCallback scheduling | Browser / Client (inline JS) | — | Browser API; Python only produces the string |
| Twitter widget pre-initialization | Browser / Client (inline JS) | — | `twttr.widgets` is a CDN-loaded widget library |
| Pool eviction | Browser / Client (inline JS) | — | Pure in-memory JS logic |
| String-grep test verification | Python test layer | — | `pytest` reads generated `index.html` as text |

---

## Standard Stack

### Core

All implementation is in existing stack — no new libraries needed.

| Component | Source | Purpose |
|-----------|--------|---------|
| `requestIdleCallback` (browser built-in) | Browser API | Schedule prefetch without blocking render |
| `Map` (browser built-in) | Browser API | O(1) pool lookup by postId |
| `twttr.widgets.load(element)` | Twitter platform CDN (already loaded) | Pre-initialize widgets in hidden container |
| `renderPost(post, rs)` (existing) | `static_export.py` inline JS | Generate card HTML for pool nodes |
| `allPosts` / `reviewMap` (existing) | `static_export.py` inline JS | Data available in prefetch worker scope |

**No new Python packages or npm installs required.** [VERIFIED: codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
User navigates (click / keyboard / swipe)
        │
        ▼
renderCarousel(results, idx)
        │
        ├── prefetchPool.has(entry.id)?
        │       │
        │       ├── YES (pool hit) ──► retrieve node, delete from pool
        │       │                      DOM insertion (not innerHTML)
        │       │                      warm-state check ──► skip or call loadTwitterWidget()
        │       │
        │       └── NO (pool miss) ──► existing innerHTML path
        │                              loadTwitterWidget() as before
        │
        └── schedulePrefetch(results, idx)
                │
                ▼ (idle callback, max 200ms delay)
            _runPrefetch(results, idx)
                │
                ├── compute window [idx-2 .. idx+5], clamp to bounds
                ├── evict pool entries outside window
                ├── for each new idx in window (not already in pool):
                │     renderPost() → div.innerHTML → .post-card node
                │     insert into #prefetch-container
                │     store in prefetchPool
                └── if twttr ready: twttr.widgets.load(prefetchContainer)


Filter / Sort / Search changes
        │
        ▼
renderView()  [carousel branch]
        │
        ├── clearPrefetchPool()  ← NEW: remove nodes, clear Map, cancel timer
        └── renderCarousel(results, carouselIndex)
```

### Recommended Project Structure (JS functions, in order)

```
// Global state block (~line 777)
const PREFETCH_AHEAD = 5;
const PREFETCH_BEHIND = 2;
let prefetchPool = new Map();
let _prefetchContainer = null;
let _prefetchTimerId = null;

// New prefetch functions (add after loadTwitterWidget ~line 1033)
function _getPrefetchContainer()   // lazy-init #prefetch-container
function clearPrefetchPool()       // evict all, cancel timer
function _runPrefetch(results, idx)  // compute window, build nodes, warm widgets
function schedulePrefetch(results, idx)  // requestIdleCallback wrapper

// Modified renderCarousel (~line 1083)
// - Add pool hit/miss at top
// - Add schedulePrefetch(results, idx) at bottom (after event listener setup)

// Modified renderView (~line 1188 carousel branch)
// - Add clearPrefetchPool() before renderCarousel()
```

### Pattern 1: requestIdleCallback with setTimeout fallback

**What:** Schedule a callback to run during browser idle time, with a maximum wait before forcing execution.

**When to use:** Non-critical background work that should not compete with render-critical tasks.

```javascript
// Source: D-04 from CONTEXT.md (established browser API pattern)
function schedulePrefetch(results, idx) {
  // Cancel any pending prefetch before scheduling new one
  if (_prefetchTimerId !== null) {
    if (typeof cancelIdleCallback !== 'undefined') {
      cancelIdleCallback(_prefetchTimerId);
    } else {
      clearTimeout(_prefetchTimerId);
    }
    _prefetchTimerId = null;
  }
  const cb = () => _runPrefetch(results, idx);
  if (typeof requestIdleCallback !== 'undefined') {
    _prefetchTimerId = requestIdleCallback(cb, { timeout: 200 });
  } else {
    _prefetchTimerId = setTimeout(cb, 200);
  }
}
```

### Pattern 2: DOM node construction from HTML string

**What:** Turn `renderPost()` HTML output into a live DOM node to store in the pool.

**When to use:** When you need a reusable DOM node from a function that returns an HTML string.

```javascript
// Source: D-07 from CONTEXT.md, standard DOM pattern
const tmp = document.createElement('div');
tmp.innerHTML = renderPost(post, rs);
const cardNode = tmp.firstElementChild;  // the .post-card div
```

### Pattern 3: Pool hit — explicit DOM insertion (not innerHTML)

**What:** When a pool node is found, rebuild the post-list container using DOM node appends rather than innerHTML, so the pre-rendered subtree is preserved intact.

**When to use:** On every carousel render when `prefetchPool.has(entry.id)` is true.

```javascript
// Source: D-07 from CONTEXT.md
const cardNode = prefetchPool.get(entry.id);
prefetchPool.delete(entry.id);
// Parse nav scaffolding via temp div
const t = document.createElement('div');
t.innerHTML = topNav + '<div></div>' + nav;
const topNavNode = t.children[0];
const navNode    = t.children[2];
const container  = document.getElementById('post-list');
container.innerHTML = '';
container.appendChild(topNavNode);
container.appendChild(cardNode);
container.appendChild(navNode);
// Re-attach event listeners by ID as usual (unchanged)
```

### Pattern 4: Warm-state detection

**What:** After inserting a pool node, check whether the Twitter widget already rendered.

**When to use:** Immediately after DOM insertion of a pool-hit node, before deciding whether to call `loadTwitterWidget()`.

```javascript
// Source: D-08 from CONTEXT.md
if (post.oembed_html && !cardNode.querySelector('blockquote.twitter-tweet')) {
  // Widget already rendered as iframe — skip loadTwitterWidget()
} else if (post.oembed_html) {
  // Widget not yet warmed — call existing path
  loadTwitterWidget();
}
```

### Pattern 5: Pool eviction during `_runPrefetch`

**What:** Remove pool entries whose postIds are no longer in the new prefetch window.

**When to use:** At the start of `_runPrefetch`, before building new entries.

```javascript
// Source: D-07, D-10 from CONTEXT.md
const windowStart = Math.max(0, idx - PREFETCH_BEHIND);
const windowEnd   = Math.min(results.length - 1, idx + PREFETCH_AHEAD);
const windowIds   = new Set(results.slice(windowStart, windowEnd + 1).map(e => e.id));
// Evict entries outside window
for (const [id, node] of prefetchPool) {
  if (!windowIds.has(id)) {
    node.remove();
    prefetchPool.delete(id);
  }
}
```

### Anti-Patterns to Avoid

- **Calling `loadTwitterWidget()` for prefetch warming:** `loadTwitterWidget()` calls `document.querySelectorAll('.oembed-container').forEach(_setupSkeletonFallback)`, which starts 5-second fallback timers for every oembed container in the prefetch container. Use `twttr.widgets.load(prefetchContainer)` directly. [VERIFIED: codebase, lines 1004-1006]
- **Passing a detached element to `twttr.widgets.load()`:** The element must be in the DOM. `#prefetch-container` must be appended to `document.body` before calling `twttr.widgets.load(prefetchContainer)`. [VERIFIED: CONTEXT.md D-03]
- **Using innerHTML to insert a pool node:** innerHTML on the parent container replaces existing nodes and discards the pre-rendered subtree reference. Use explicit `appendChild`. [VERIFIED: CONTEXT.md D-07]
- **Clearing pool on every `renderCarousel` call:** Pool must only be cleared in `renderView()`, not on direct navigation calls. [VERIFIED: CONTEXT.md D-09]
- **Skipping timer cancellation on rapid navigation:** Without `cancelIdleCallback` / `clearTimeout`, rapid swiping queues multiple `_runPrefetch` calls that race each other. [VERIFIED: CONTEXT.md D-04, D-10]
- **Zero or negligible width on `#prefetch-container`:** Twitter widgets may not render if the container has zero width. Use `width:500px`. [VERIFIED: CONTEXT.md specifics]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idle scheduling | Custom polling / zero-delay setInterval | `requestIdleCallback` + `setTimeout(cb, 200)` fallback | Already a browser standard; fallback covers Safari/Firefox compat |
| Widget warming API | Any wrapper that re-invokes `loadTwitterWidget` | `twttr.widgets.load(element)` directly | `loadTwitterWidget` has side effects (skeleton fallback timers) inappropriate for hidden nodes |
| Post HTML → DOM node | Calling `renderPost` multiple times or building HTML manually | `createElement + innerHTML` on temp div | `renderPost` already returns complete HTML strings |

---

## Common Pitfalls

### Pitfall 1: `cancelIdleCallback` vs `clearTimeout` mismatch

**What goes wrong:** The timer id from `requestIdleCallback()` must be cancelled with `cancelIdleCallback()`, and a `setTimeout()` id with `clearTimeout()`. Mixing them is a no-op — the timer fires anyway.

**Why it happens:** The feature-detect branch (`typeof requestIdleCallback !== 'undefined'`) stores the id but a naive implementation always calls `clearTimeout()`.

**How to avoid:** Track which API was used, OR track both separately. Simplest: track via a boolean alongside the id, or always use the same cancel call based on the same feature detect.

**Warning signs:** Rapid navigation triggers multiple `_runPrefetch` calls — visible as extra DOM nodes appearing in `#prefetch-container` beyond the expected 7.

### Pitfall 2: Pool node still attached to `#prefetch-container` when moved to `#post-list`

**What goes wrong:** A DOM node can only have one parent. `appendChild(cardNode)` on `#post-list` automatically detaches it from `#prefetch-container`. This is correct behavior, but the pool Map still holds the reference — `prefetchPool.delete(entry.id)` must happen before or immediately after.

**Why it happens:** Forgetting to `delete` the pool entry after retrieval. The Map now holds a reference to a node that lives in `#post-list`, not `#prefetch-container`. On next `clearPrefetchPool()`, calling `.remove()` on that stale node would silently succeed (removing the rendered card from view).

**How to avoid:** `prefetchPool.delete(entry.id)` immediately after `prefetchPool.get(entry.id)`.

### Pitfall 3: `_setupSkeletonFallback` timers on prefetch nodes

**What goes wrong:** Calling `loadTwitterWidget()` for widget warming triggers a `document.querySelectorAll('.oembed-container').forEach(_setupSkeletonFallback)` call, starting 5-second timers for every `.oembed-container` in the prefetch container. These fire even after pool eviction, potentially calling `.classList.add('widget-ready')` on detached nodes (harmless but wasteful) or still-live nodes.

**Why it happens:** `loadTwitterWidget()` is designed for the main post-list, where all oembed-containers need skeleton fallback. It is not scoped to a specific element.

**How to avoid:** Use `twttr.widgets.load(prefetchContainer)` directly. Never call `loadTwitterWidget()` from `_runPrefetch`.

### Pitfall 4: Pool built before `allPosts` is populated

**What goes wrong:** `_runPrefetch` calls `allPosts[entry.id]` — if the Bootstrap Promise hasn't resolved yet, `allPosts` is still `{}` and all lookups return `undefined`, causing `renderPost(undefined, ...)` to crash.

**Why it happens:** `schedulePrefetch` is called from `renderCarousel`, which is only called after Bootstrap resolves. So this is NOT actually a risk — but the pitfall is adding `schedulePrefetch` elsewhere (e.g., in event listener setup code that fires before Bootstrap). 

**How to avoid:** Only call `schedulePrefetch` from within `renderCarousel` (after the Bootstrap Promise resolves). The current design (called at the end of `renderCarousel`) is safe.

### Pitfall 5: `renderView`'s early-return paths bypass `clearPrefetchPool`

**What goes wrong:** `renderView()` has two early returns for `total === 0` and `filtered === 0`. If `clearPrefetchPool()` is placed AFTER these guards, a filter change that yields zero results will leave stale pool nodes alive.

**Why it happens:** Placing `clearPrefetchPool()` only inside the `if (currentMode === 'carousel')` block, which is reached AFTER the zero-results guard.

**How to avoid:** The CONTEXT.md decision (D-09) says "at the start of the carousel branch in `renderView()`" — meaning inside the `if (currentMode === 'carousel')` block, before `renderCarousel()`. This is correct: if `filtered === 0`, we return before entering carousel branch anyway and the pool becomes stale but harmless (it won't be used until `renderCarousel` runs again). This is acceptable — the only cost is holding a few hidden nodes in memory temporarily.

---

## Code Examples

### Complete `_getPrefetchContainer`

```javascript
// Source: CONTEXT.md Claude's Discretion — lazy-init pattern
function _getPrefetchContainer() {
  if (_prefetchContainer) return _prefetchContainer;
  _prefetchContainer = document.createElement('div');
  _prefetchContainer.id = 'prefetch-container';
  _prefetchContainer.style.cssText =
    'position:absolute;left:-9999px;top:-9999px;width:500px;visibility:hidden;pointer-events:none;';
  document.body.appendChild(_prefetchContainer);
  return _prefetchContainer;
}
```

### Complete `clearPrefetchPool`

```javascript
// Source: CONTEXT.md D-09, D-10
function clearPrefetchPool() {
  if (_prefetchTimerId !== null) {
    if (typeof cancelIdleCallback !== 'undefined') {
      cancelIdleCallback(_prefetchTimerId);
    } else {
      clearTimeout(_prefetchTimerId);
    }
    _prefetchTimerId = null;
  }
  for (const node of prefetchPool.values()) {
    node.remove();
  }
  prefetchPool.clear();
}
```

### Test pattern for PREFETCH-08

```python
# Source: established pattern in TestIndexHtmlCarousel (test_static_export_service.py)
class TestIndexHtmlPrefetch:
    """Tests for prefetch pool additions to index.html. PREFETCH-08."""

    def test_schedule_prefetch_function_present(self, temp_db_v6, tmp_path):
        """PREFETCH-08: schedulePrefetch function present in generated HTML."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "schedulePrefetch" in html

    def test_prefetch_pool_variable_present(self, temp_db_v6, tmp_path):
        """PREFETCH-08: prefetchPool variable present in generated HTML."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "prefetchPool" in html
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python) |
| Config file | `pyproject.toml` |
| Quick run command | `python -m pytest tests/test_static_export_service.py -x -q` |
| Full suite command | `python -m pytest --tb=short -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PREFETCH-01 | `schedulePrefetch` function present in index.html | string-grep (unit) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_schedule_prefetch_function_present -x` | ❌ Wave 0 |
| PREFETCH-02 | `PREFETCH_BEHIND` or window logic present in index.html | string-grep (unit) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch -x` | ❌ Wave 0 |
| PREFETCH-03 | `twttr.widgets.load` called in prefetch context | string-grep (unit) | already covered by `test_oembed_reinit_called_in_carousel` (existing) | ✅ |
| PREFETCH-04 | `requestIdleCallback` present in index.html | string-grep (unit) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_request_idle_callback_present -x` | ❌ Wave 0 |
| PREFETCH-05 | `prefetchPool.has` present in index.html | string-grep (unit) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_prefetch_pool_hit_check_present -x` | ❌ Wave 0 |
| PREFETCH-06 | `clearPrefetchPool` called in `renderView` context | string-grep (unit) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_clear_prefetch_pool_present -x` | ❌ Wave 0 |
| PREFETCH-07 | Pool eviction logic present (entries outside window removed) | string-grep (unit) | covered by `prefetchPool.delete` presence check | ❌ Wave 0 |
| PREFETCH-08 | `schedulePrefetch` + `prefetchPool` identifiers in HTML | string-grep (unit) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_static_export_service.py -x -q`
- **Per wave merge:** `python -m pytest --tb=short -q`
- **Phase gate:** Full suite green before phase sign-off

### Wave 0 Gaps

- [ ] `tests/test_static_export_service.py` — add `TestIndexHtmlPrefetch` class with tests for PREFETCH-01 through PREFETCH-08 string identifiers. No new file needed — add class to existing file.

---

## Security Domain

This phase is purely client-side JavaScript within a static HTML export. No server, no new network requests, no new input surfaces. No new ASVS controls are introduced.

| ASVS Category | Applies | Notes |
|---------------|---------|-------|
| V2 Authentication | no | Static viewer, no auth |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No new routes or endpoints |
| V5 Input Validation | no | Prefetch reads from already-validated `allPosts` / `reviewMap` globals |
| V6 Cryptography | no | No crypto |

**Threat relevant to this phase:** XSS via pre-rendered card nodes. Mitigation: `renderPost()` already uses `esc()` for all user-controlled fields — prefetch nodes are built via the same path, inheriting existing XSS protection. [VERIFIED: codebase, `esc()` function at line ~755, used throughout all render functions]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `requestIdleCallback` is unavailable in Safari (historically) — the `setTimeout(cb, 200)` fallback is required for mobile Safari users | Standard Stack | If Safari now supports it, fallback is harmless but unused |
| A2 | `cancelIdleCallback` is available when `requestIdleCallback` is available | Code Examples | If not always paired, need separate feature detect for cancel |

---

## Open Questions

1. **`cancelIdleCallback` pairing guarantee**
   - What we know: `requestIdleCallback` is supported in Chrome, Edge, Firefox 119+; not in Safari (as of training)
   - What's unclear: Is `cancelIdleCallback` always present alongside `requestIdleCallback` in all browsers that support it?
   - Recommendation: Use the same `typeof requestIdleCallback !== 'undefined'` guard for the cancel call — browsers that ship `requestIdleCallback` ship `cancelIdleCallback` as part of the same spec [ASSUMED]. The fallback path using `clearTimeout` handles the else branch.

2. **Pool node count during rapid navigation**
   - What we know: Window is ≤7 nodes; `_runPrefetch` evicts out-of-window entries; PREFETCH-07 requires this bound
   - What's unclear: If the user navigates faster than the 200ms idle deadline, multiple `_runPrefetch` calls could queue
   - Recommendation: Timer cancellation in `schedulePrefetch` handles this — each navigation cancels the previous pending prefetch before scheduling a new one. At most one `_runPrefetch` will be in-flight at a time. [VERIFIED: D-04]

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely inline JS within a Python string. No external CLI tools, services, or runtimes beyond the project's existing Python + pytest stack.

---

## Sources

### Primary (HIGH confidence)
- `src/services/static_export.py` lines 777–1299 — verified current JS structure, global state block, `renderCarousel`, `renderView`, `loadTwitterWidget`, `_setupSkeletonFallback` implementations
- `.planning/phases/18-background-prefetch/18-CONTEXT.md` — all decisions locked, verified by direct read
- `tests/test_static_export_service.py` — verified existing test class patterns (`TestIndexHtmlCarousel`, `TestIndexHtmlDeepLink`) for PREFETCH-08 implementation model

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — PREFETCH-01 through PREFETCH-08 definitions confirmed
- `.planning/ROADMAP.md` — Phase 18 success criteria confirmed

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all components verified in codebase
- Architecture: HIGH — decisions locked in CONTEXT.md; integration points verified by code inspection
- Pitfalls: HIGH — derived from concrete code paths verified in static_export.py

**Research date:** 2026-07-18
**Valid until:** Stable — implementation is self-contained, no external dependency churn risk
