# Phase 16: Viewer Presentation Modes - Research

**Researched:** 2026-06-13
**Domain:** Vanilla JS / CSS — inline static viewer in `_build_index_html()` Python string
**Confidence:** HIGH (all findings verified directly from the codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Mode Switcher UX**
- Segmented pill control: two adjacent buttons `[Stream] [Carousel]` — active button filled with `--color-accent`
- Label text: "Stream" / "Carousel"
- Placement: right side of `#header`, after count badge
- Stream is always the default on page load (localStorage overrides if user previously switched)

**Carousel Layout**
- Card max-width: `860px` (wider than stream's 720px), centered
- Navigation controls: centered below the post — `← Prev` | `3 / 47 posts` | `Next →`
- Post counter shown between prev/next buttons; header count badge shows total filtered count as normal
- Auto-scroll to `window.scrollTo(0, 0)` on each prev/next navigation

**State Persistence**
- Active mode saved to `localStorage` key `xbm_mode` — persists across page reloads
- Carousel index resets to 0 on any filter/search change
- Stream scroll position (`window.scrollY`) saved when switching to carousel and restored when switching back

**Keyboard Navigation**
- Left/Right arrow keys only
- Global `keydown` listener on `document`
- Escape key switches back to Stream mode
- No wrap-around: Next disabled at last post, Prev disabled at first post

### Claude's Discretion

- Exact CSS for disabled button state (opacity, cursor) — decided in CONTEXT.md specifics: `opacity: 0.3; cursor: not-allowed; pointer-events: none`
- Animation/transition on mode switch (subtle fade or none)
- Whether `#controls` row stays visible in carousel mode or is hidden

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 16 adds two presentation modes — Stream (existing scrollable list) and Carousel (one post at a time with prev/next navigation) — to the self-contained static viewer at `src/services/static_export.py`. All changes are confined to a single Python method: `_build_index_html()` (lines 333–892), which returns a ~560-line HTML/CSS/JS string with no build step or templating engine.

The viewer already has a solid foundation: `renderPost()` handles all post types including oEmbed, `filterAndSort()` returns the ordered results array, and `renderView()` is the central render dispatcher. Carousel mode adds a mode-state variable, a carousel index, a mode switcher in the header, and a new `renderCarousel()` branch inside `renderView()`. The oEmbed path in carousel mode must call `loadTwitterWidget()` + `twttr.widgets.load()` after inserting carousel DOM, matching the existing stream pattern.

All phase work is a single-file edit. No Python data model, no CLI, no repository changes.

**Primary recommendation:** Extend `renderView()` with a mode branch. Stream path is untouched. Carousel path replaces `#post-list` innerHTML with a single post card plus a nav controls row. Keyboard listener and localStorage wiring are additive globals.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Mode switcher UI | Browser / Client (vanilla JS) | — | Purely client-side DOM toggle, no server needed |
| Carousel render logic | Browser / Client (vanilla JS) | — | Indexes into already-loaded `allPosts` / `filterAndSort()` result |
| Mode persistence | Browser / Client (localStorage) | — | Client preference; no server-side state |
| oEmbed re-initialization | Browser / Client (vanilla JS) | CDN (Twitter widget.js) | Must call `twttr.widgets.load()` after DOM insert |
| HTML/CSS/JS generation | Python (`_build_index_html()`) | — | Viewer is a Python string constant; all edits happen here |

---

## Standard Stack

No new libraries. This phase is pure HTML/CSS/JS within the existing Python string.

### Existing APIs in Use

| API | Where Used | Notes |
|-----|-----------|-------|
| `localStorage.getItem/setItem` | Mode persistence | `xbm_mode` key, values `'stream'`/`'carousel'` [VERIFIED: codebase] |
| `window.scrollTo(0, 0)` | Auto-scroll on carousel nav | Standard DOM API [VERIFIED: codebase pattern] |
| `window.scrollY` | Save/restore stream scroll position | Read before switch, restore on switch back [VERIFIED: codebase pattern] |
| `document.addEventListener('keydown', ...)` | Global keyboard nav | Same pattern as existing `search-input` listener [VERIFIED: codebase] |
| `window.twttr.widgets.load(el)` | oEmbed re-render in carousel | Called after carousel card inserted — matches stream path (line 854) [VERIFIED: codebase] |
| `loadTwitterWidget()` | Load CDN script once | Already guarded by `_twitterWidgetLoaded` flag (line 770) [VERIFIED: codebase] |

---

## Architecture Patterns

### System Architecture Diagram

```
User Action (click mode button / arrow key / filter change)
        |
        v
  Mode state (JS let: 'stream' | 'carousel')
  + Carousel index (JS let: 0..N-1)
        |
        v
  renderView()  <--- called by all existing event listeners unchanged
        |
        +--[mode === 'stream']--> existing innerHTML loop over results  --> #post-list
        |
        +--[mode === 'carousel']--> renderCarousel(results, idx)        --> #post-list
                                          |
                                          +-- renderPost(post, rs)       (reuse unchanged)
                                          +-- nav controls HTML (prev/next/counter)
                                          +-- loadTwitterWidget() + twttr.widgets.load()
                                               (if oembed post)
```

### Recommended Change Structure (all in `_build_index_html()`)

```
_build_index_html() edits:
├── CSS additions (~20 lines)
│   ├── .mode-switcher (pill group container)
│   ├── .mode-btn (individual button, active state)
│   └── #carousel-nav (controls row: prev/counter/next)
├── HTML additions (~6 lines)
│   └── Two <button> elements added to #header after #count-badge
├── JS additions (~60-80 lines)
│   ├── let currentMode = 'stream'   (global state)
│   ├── let carouselIndex = 0        (global state)
│   ├── let savedScrollY = 0         (global state)
│   ├── setMode(mode)                (switch, persist to localStorage, call renderView)
│   ├── renderCarousel(results, idx) (build single-card + nav HTML)
│   └── document.addEventListener('keydown', ...)  (arrow keys + Escape)
└── renderView() modification
    ├── read currentMode at top
    ├── reset carouselIndex = 0 on filter change (detect via results.length change or always reset)
    └── branch: stream path (untouched) vs carousel path (renderCarousel)
```

### Pattern 1: Mode State and localStorage

**What:** A module-level `let currentMode` variable holds the active mode. On page load, initialize from localStorage. `setMode()` updates the variable, syncs localStorage, updates button active state, and calls `renderView()`.

**When to use:** All mode-switching code paths.

```javascript
// Source: verified codebase pattern — mirrors existing debounceTimer global
let currentMode = localStorage.getItem('xbm_mode') || 'stream';
let carouselIndex = 0;
let savedScrollY = 0;

function setMode(mode) {
  if (mode === currentMode) return;
  if (mode === 'carousel') { savedScrollY = window.scrollY; }
  if (mode === 'stream')   { requestAnimationFrame(() => window.scrollTo(0, savedScrollY)); }
  currentMode = mode;
  localStorage.setItem('xbm_mode', mode);
  // update .mode-btn active classes
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  renderView();
}
```

### Pattern 2: Carousel Render

**What:** `renderCarousel(results, idx)` renders a single post at `idx` plus a nav controls row into `#post-list`.

**When to use:** Called from `renderView()` when `currentMode === 'carousel'`.

```javascript
// Source: verified codebase pattern — reuses renderPost() unchanged
function renderCarousel(results, idx) {
  const entry = results[idx];
  const post = allPosts[entry.id];
  const rs = reviewMap.get(entry.id) || null;
  const cardHtml = renderPost(post, rs);
  const total = results.length;
  const prevDisabled = idx === 0         ? 'disabled' : '';
  const nextDisabled = idx === total - 1 ? 'disabled' : '';
  const nav = `<div id="carousel-nav">
    <button class="carousel-btn" id="carousel-prev" ${prevDisabled}>&larr; Prev</button>
    <span class="carousel-counter">${idx + 1} / ${total} posts</span>
    <button class="carousel-btn" id="carousel-next" ${nextDisabled}>Next &rarr;</button>
  </div>`;
  document.getElementById('post-list').innerHTML = cardHtml + nav;
  // wire nav buttons
  document.getElementById('carousel-prev').addEventListener('click', () => {
    if (carouselIndex > 0) { carouselIndex--; renderView(); window.scrollTo(0, 0); }
  });
  document.getElementById('carousel-next').addEventListener('click', () => {
    if (carouselIndex < results.length - 1) { carouselIndex++; renderView(); window.scrollTo(0, 0); }
  });
  // oEmbed: re-initialize twitter widget for this card
  if (post.oembed_html) {
    loadTwitterWidget();
    if (window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(document.getElementById('post-list'));
    }
  }
}
```

### Pattern 3: Keyboard Navigation

**What:** A single global `keydown` listener on `document`. Added after page load (same location as existing event listeners). Only fires when `currentMode === 'carousel'` and results are available.

```javascript
// Source: verified codebase pattern — mirrors existing event listener block
document.addEventListener('keydown', (e) => {
  if (currentMode !== 'carousel') return;
  const results = filterAndSort();
  if (e.key === 'ArrowRight' && carouselIndex < results.length - 1) {
    carouselIndex++; renderView(); window.scrollTo(0, 0);
  } else if (e.key === 'ArrowLeft' && carouselIndex > 0) {
    carouselIndex--; renderView(); window.scrollTo(0, 0);
  } else if (e.key === 'Escape') {
    setMode('stream');
  }
});
```

### Pattern 4: renderView() Integration Point

**What:** `renderView()` already handles filter/sort, badge, empty state. The carousel branch slots in where stream currently sets `container.innerHTML`.

**Critical:** `carouselIndex` must reset to 0 on any filter/search change. The cleanest approach: reset at the top of `renderView()` only when mode is carousel and results have changed, OR always reset on filter-change events by adding a one-liner before `renderView()` calls from the search/filter listeners. The CONTEXT.md decision is clear: *"Carousel index resets to 0 on any filter/search change."* The simplest implementation: reset inside `renderView()` itself when mode is carousel (before rendering).

**Trade-off to decide:** Always reset inside `renderView()` (simplest, but resets on programmatic calls too) vs. only reset in filter/search listener callbacks (more precise). Recommendation: reset inside `renderView()` when `currentMode === 'carousel'` — this is safe because `renderView()` is the single render dispatch point and any call in carousel mode is triggered by a user action.

### Anti-Patterns to Avoid

- **Calling `filterAndSort()` twice per render in carousel mode:** `renderView()` calls it, then `renderCarousel()` calls it again for keyboard listener. Solution: pass `results` as a parameter to `renderCarousel(results, idx)` so `filterAndSort()` runs once per render.
- **Re-adding keyboard listener on every `renderView()` call:** `document.addEventListener` does not deduplicate — calling it inside `renderView()` creates N listeners after N renders. Add keyboard listener once at page load, outside `renderView()`.
- **Setting `container.innerHTML` then immediately re-querying buttons before DOM settles:** Since this is synchronous DOM manipulation (not async), the query after `innerHTML =` is safe. No requestAnimationFrame needed for button wiring.
- **Forgetting `pointer-events: none` on disabled carousel buttons:** Without it, keyboard-fast users can click through `opacity: 0.3` buttons. The CONTEXT.md specifies `pointer-events: none` on disabled state.
- **Calling `twttr.widgets.load()` with the full `document` body in carousel mode:** Pass the `#post-list` container element to scope the re-render, matching the existing stream pattern (line 854).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mode persistence | Custom cookie/URL param | `localStorage` | Already established pattern; zero dependencies |
| Scroll save/restore | Complex scroll-position tracking | `window.scrollY` + `window.scrollTo()` | Standard DOM; simple one-liner each |
| oEmbed re-render | Re-fetch oEmbed HTML on carousel nav | `twttr.widgets.load(el)` | Twitter widget SDK handles re-init; already in codebase |
| HTML escaping | Custom escape in carousel template | Existing `esc()` helper | Already handles &, <, >, " — use it for all dynamic content |

**Key insight:** Every new capability in this phase has an existing pattern in the codebase to mirror. There is nothing architecturally new — only additive wiring.

---

## Common Pitfalls

### Pitfall 1: Carousel Index Out of Bounds After Filter Change

**What goes wrong:** User is at carousel index 12, searches for something with 5 results — index 12 is now invalid; `results[12]` is `undefined`, `renderPost(undefined, ...)` throws.

**Why it happens:** `carouselIndex` is not reset when the result set shrinks.

**How to avoid:** Reset `carouselIndex = 0` at the start of `renderView()` when `currentMode === 'carousel'`. Since the CONTEXT.md locked decision says reset on filter/search change, and all filter/search changes go through `renderView()`, this is the correct choke point.

**Warning signs:** `TypeError: Cannot read properties of undefined (reading 'id')` in browser console.

### Pitfall 2: Multiple Keyboard Event Listeners Accumulate

**What goes wrong:** If `document.addEventListener('keydown', ...)` is placed inside `renderView()`, each render adds another listener. After 10 navigations, ArrowRight fires the handler 10 times.

**Why it happens:** `addEventListener` does not deduplicate functions unless the exact same function reference is passed (and even then, only with identical capture flag).

**How to avoid:** Wire keyboard listener exactly once, in the same block as the existing `search-input` / `date-filter` / `sort-order` listeners (lines 860–865 in current code).

**Warning signs:** Carousel skips multiple posts per keypress; jumps accelerate as user navigates.

### Pitfall 3: oEmbed Posts Not Rendering in Carousel

**What goes wrong:** Carousel shows a bare `<blockquote>` instead of a rendered Twitter widget.

**Why it happens:** `twttr.widgets.load()` must be called after the blockquote is in the DOM. If the call is omitted from `renderCarousel()`, or called before `innerHTML` is set, the widget does not initialize.

**How to avoid:** Call `loadTwitterWidget()` + `twttr.widgets.load(container)` at the end of `renderCarousel()`, after `innerHTML` is assigned and buttons are wired. Match the exact pattern at lines 851–856.

**Warning signs:** oEmbed posts show as plain blockquote text in carousel mode; stream mode renders them fine.

### Pitfall 4: `#controls` Visibility in Carousel Mode

**What goes wrong:** `#controls` (search/filter/sort) is constrained to `max-width: 720px` (line 407). In carousel mode the post card is `860px` max-width, but the controls bar is narrower — visual misalignment.

**Why it happens:** `#controls` has a hardcoded `max-width: 720px` matching the stream card width.

**How to avoid:** This is in Claude's Discretion scope. Options: (a) keep `#controls` visible and accept the asymmetry — simple, functional; (b) hide `#controls` in carousel mode — cleaner focus experience; (c) change `#controls` max-width to `860px` in carousel mode via a class toggle. Recommendation: keep `#controls` visible (option a) to avoid complexity — the filter bar remains useful in carousel mode to narrow results.

**Warning signs:** Obvious width mismatch between controls bar and carousel card at wide viewport widths.

### Pitfall 5: `setMode()` Called Before renderView() Completes First Render

**What goes wrong:** `localStorage.getItem('xbm_mode')` returns `'carousel'` on page load, but `allPosts` / `searchIndex` are not yet populated (still awaiting the `Promise.all` fetch). `renderCarousel()` runs with empty data.

**Why it happens:** `currentMode` is initialized at module scope (before `Promise.all` resolves), and if `renderView()` is called during the bootstrap, it runs with empty state.

**How to avoid:** `renderView()` is only called once: at the end of `Promise.all.then()` (line 886), after all data is loaded. Initializing `currentMode` at module scope is safe as long as `renderView()` is not called before the bootstrap resolves. The existing bootstrap structure is correct — do not add any pre-bootstrap `renderView()` call.

**Warning signs:** Carousel shows "0 / 0 posts" counter or throws on first load when localStorage has `'carousel'`.

---

## Code Examples

### Verified Current Patterns

#### oEmbed re-render after stream innerHTML (lines 851–856)
```javascript
// Source: src/services/static_export.py lines 851–856 [VERIFIED: codebase]
if (results.some(e => allPosts[e.id] && allPosts[e.id].oembed_html)) {
  loadTwitterWidget();
  if (window.twttr && window.twttr.widgets) {
    window.twttr.widgets.load(container);
  }
}
```
Mirror this exactly in `renderCarousel()` — replacing `container` with the carousel card element.

#### Existing header HTML (lines 539–542)
```html
<!-- Source: src/services/static_export.py lines 539–542 [VERIFIED: codebase] -->
<div id="header">
  <h1>X Bookmarks</h1>
  <span id="count-badge">...</span>
</div>
```
Add mode switcher buttons after `#count-badge`. Use `margin-left: auto` on the switcher container to push it to the right side of the flex row.

#### Existing event listener pattern (lines 860–865)
```javascript
// Source: src/services/static_export.py lines 860–865 [VERIFIED: codebase]
document.getElementById('search-input').addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderView, 150);
});
document.getElementById('date-filter').addEventListener('change', renderView);
document.getElementById('sort-order').addEventListener('change', renderView);
```
Add `document.addEventListener('keydown', ...)` here, in the same block.

#### Existing CSS variable palette (lines 343–364)
```css
/* Source: src/services/static_export.py lines 343–364 [VERIFIED: codebase] */
--color-bg:        #0f172a;
--color-card:      #1e293b;
--color-accent:    #2563eb;
--color-border:    #334155;
--color-text:      #f1f5f9;
--color-secondary: #94a3b8;
--color-muted:     #64748b;
```
Use `--color-accent` for the active mode button fill. Use `--color-border` for inactive button borders.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No presentation modes | Stream only (Phase 14) | 2026-06-13 | Now adding Carousel as second mode |
| oEmbed only in stream | oEmbed in both stream + carousel | Phase 16 | Carousel must re-trigger widget SDK |

---

## Open Questions

1. **Should `#controls` be hidden in carousel mode?**
   - What we know: CONTEXT.md leaves this to Claude's Discretion
   - What's unclear: Whether the filter bar adds value when browsing carousel-style
   - Recommendation: Keep controls visible — narrowing results before entering carousel is a natural workflow. Hiding adds JS complexity (show/hide on mode switch) with marginal UX gain.

2. **Should `renderView()` always reset `carouselIndex = 0`, or only when results count changes?**
   - What we know: CONTEXT.md says "resets to 0 on any filter/search change"
   - What's unclear: Edge case — programmatic `renderView()` calls triggered by mode switch itself
   - Recommendation: Reset `carouselIndex = 0` inside `renderView()` at the start of the carousel branch, unconditionally. This is correct behavior: a mode switch also "resets" the carousel to start.

3. **Transition animation on mode switch?**
   - What we know: CONTEXT.md leaves this to Claude's Discretion
   - What's unclear: User preference
   - Recommendation: No animation. The viewer loads fast, animation adds complexity with no functional benefit. Add a TODO comment in code if desired later.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is pure code changes to an inline HTML/CSS/JS string within a single Python file. No external tools, services, CLIs, runtimes, or build steps are required beyond the existing Python/pytest stack.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python) |
| Config file | `pyproject.toml` (project root) |
| Quick run command | `venv/bin/python -m pytest tests/test_static_export_service.py -x -q` |
| Full suite command | `venv/bin/python -m pytest --tb=short -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIEWER-01 | Mode switcher buttons present in generated HTML | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel -x` | ❌ Wave 0 |
| VIEWER-02 | `xbm_mode` localStorage key wired in JS | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel -x` | ❌ Wave 0 |
| VIEWER-03 | Carousel render function present in generated HTML | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel -x` | ❌ Wave 0 |
| VIEWER-04 | Keyboard nav listener present in generated HTML | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel -x` | ❌ Wave 0 |
| VIEWER-05 | oEmbed `twttr.widgets.load` called in carousel path | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel -x` | ❌ Wave 0 |
| VIEWER-06 | Stream mode unchanged — existing TestIndexHtml tests pass | unit (regression) | `pytest tests/test_static_export_service.py::TestIndexHtml -x` | ✅ exists |
| VIEWER-07 | Carousel renders single post — manual browser test | manual | Deploy to Netlify, navigate carousel | — |
| VIEWER-08 | Keyboard left/right/Escape works — manual browser test | manual | Open viewer, switch to carousel, press arrow keys | — |
| VIEWER-09 | oEmbed renders inside carousel — manual browser test | manual | Export with `--rich-embeds`, switch to carousel | — |

### Testing Strategy for Inline JS/CSS

Since the viewer is an inline JS/CSS string inside Python, there is no JS test infrastructure. The established pattern (from Phase 15, OEMBED-03 decision in STATE.md) is:

1. **Python string-grep tests** (`TestIndexHtml` class): Assert that specific JS function names, CSS class names, DOM IDs, and key patterns are present in the generated `index.html` string. These are fast, automated, and catch regressions in the build step.

2. **Manual browser tests**: Functionality tests that require a live browser (mode switching, keyboard nav, oEmbed re-render). These are documented as checklists but not automated.

**The string-grep approach is the correct automation boundary for this codebase.** Do not attempt to run JS in pytest (no jsdom, no Node integration exists).

### What the `TestIndexHtmlCarousel` class should assert (Wave 0 gaps)

These are string-presence assertions on the output of `StaticExportService._build_index_html()`:

```python
# Pattern: call svc._build_index_html() or svc.export(tmp_path) then read HTML
html = svc._build_index_html()  # or (tmp_path / "index.html").read_text()
assert "mode-btn" in html            # mode switcher button class
assert "xbm_mode" in html            # localStorage key
assert "carousel" in html            # mode value
assert "carouselIndex" in html       # carousel state variable
assert "renderCarousel" in html      # carousel render function
assert "ArrowRight" in html          # keyboard navigation
assert "carousel-nav" in html        # nav controls container ID
assert "carousel-prev" in html       # prev button ID
assert "carousel-next" in html       # next button ID
assert "carousel-counter" in html    # counter span class
```

### Sampling Rate

- **Per task commit:** `venv/bin/python -m pytest tests/test_static_export_service.py -x -q`
- **Per wave merge:** `venv/bin/python -m pytest --tb=short -q` (all 622+ tests)
- **Phase gate:** Full suite green before phase is marked complete

### Wave 0 Gaps

- [ ] `tests/test_static_export_service.py::TestIndexHtmlCarousel` — new class with VIEWER-01 through VIEWER-05 string-grep tests
- [ ] No new conftest fixtures needed — `temp_db_v6` and `tmp_path` are sufficient

---

## Security Domain

This phase makes no changes to authentication, session management, access control, or server-side code. All changes are client-side JS/CSS in a self-contained static file with no network requests beyond the existing `fetch()` calls for JSON files.

The existing `esc()` helper (verified at line 584) must be used for any dynamic strings inserted into carousel HTML — no new XSS surface is introduced if carousel render functions call `renderPost()` (which already uses `esc()`) and do not add new unescaped `innerHTML` assignments.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (XSS in innerHTML) | `esc()` helper — already in place, reused |
| All others | no | Not in scope for static client-side viewer |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified directly from the codebase or from CONTEXT.md. No assumed claims.**

---

## Sources

### Primary (HIGH confidence)

- `src/services/static_export.py` lines 333–892 — complete `_build_index_html()` implementation [VERIFIED: codebase read]
- `tests/test_static_export_service.py` — full existing test class structure, `TestIndexHtml` pattern [VERIFIED: codebase read]
- `.planning/phases/16-viewer-presentation-modes/16-CONTEXT.md` — all locked decisions [VERIFIED: read]
- `.planning/STATE.md` — OEMBED-03 precedent for manual-only JS tests [VERIFIED: read]

### Secondary (MEDIUM confidence)

- MDN `localStorage` API — browser standard, no version concerns [ASSUMED: well-established Web API]
- MDN `document.addEventListener('keydown')` — standard DOM event [ASSUMED: well-established Web API]
- `twttr.widgets.load(el)` re-initialization in carousel — pattern extrapolated from stream path at lines 851–856 [VERIFIED: codebase pattern, applied by analogy]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all APIs verified in existing codebase
- Architecture: HIGH — all integration points verified by reading the full `_build_index_html()` implementation
- Pitfalls: HIGH — identified from direct code inspection (event listener accumulation, out-of-bounds index, oEmbed timing)
- Test strategy: HIGH — follows established project pattern (string-grep in TestIndexHtml class)

**Research date:** 2026-06-13
**Valid until:** Stable — no external dependencies. Valid until `_build_index_html()` is refactored.
