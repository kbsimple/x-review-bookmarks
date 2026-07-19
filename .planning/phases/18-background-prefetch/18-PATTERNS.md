# Phase 18: Background Prefetch - Pattern Map

**Mapped:** 2026-07-18
**Files analyzed:** 2 (1 modified source file + 1 modified test file)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/services/static_export.py` (inline JS block) | service (inline JS producer) | event-driven | Same file — existing JS sections below | exact (self-analog) |
| `tests/test_static_export_service.py` (new class) | test | request-response | `tests/test_static_export_service.py::TestIndexHtmlCarousel` | exact |

---

## Pattern Assignments

### `src/services/static_export.py` — Global State Block Addition

**Analog:** Lines 777–792 of the same file (existing `// -- Global state --` block)

**Existing global state pattern** (lines 777–792):
```javascript
// -- Global state --
let allPosts = {};
let searchIndex = [];
let reviewMap = new Map();
let totalPostCount = 0;
let exportedDate = '';
let debounceTimer = null;
let currentMode = localStorage.getItem('xbm_mode') || 'carousel';
let carouselIndex = 0;
let savedScrollY = 0;
let cachedCarouselResults = null;
let deepLinkMode = false;
```

**New prefetch globals follow this same `let`/`const` pattern — append after line 792:**
```javascript
// -- Prefetch pool globals --
const PREFETCH_AHEAD = 5;
const PREFETCH_BEHIND = 2;
let prefetchPool = new Map();
let _prefetchContainer = null;
let _prefetchTimerId = null;
```

---

### `src/services/static_export.py` — `loadTwitterWidget()` (read-only reference: what NOT to call from prefetch)

**Analog:** Lines 1004–1033 of the same file

**Full function** (lines 1004–1033):
```javascript
function loadTwitterWidget() {
  // Set up 5s fallbacks for all current oembed-containers
  document.querySelectorAll('.oembed-container').forEach(_setupSkeletonFallback);

  if (window.twttr && window.twttr.widgets) {
    if (!_twitterRenderedBound) {
      _twitterRenderedBound = true;
      twttr.events.bind('rendered', _onWidgetRendered);
    }
    twttr.widgets.load(document.getElementById('post-list'));
    return;
  }

  if (_twitterWidgetLoaded) return;
  _twitterWidgetLoaded = true;
  const s = document.createElement('script');
  s.src = 'https://platform.twitter.com/widgets.js';
  s.async = true;
  s.charset = 'utf-8';
  s.onload = function() {
    if (window.twttr && window.twttr.events && !_twitterRenderedBound) {
      _twitterRenderedBound = true;
      twttr.events.bind('rendered', _onWidgetRendered);
    }
    if (window.twttr && window.twttr.widgets) {
      twttr.widgets.load(document.getElementById('post-list'));
    }
  };
  document.head.appendChild(s);
}
```

**Why this matters for prefetch:** The first line `document.querySelectorAll('.oembed-container').forEach(_setupSkeletonFallback)` scans ALL `.oembed-container` elements globally and starts 5-second timers on each. `_runPrefetch` must call `twttr.widgets.load(prefetchContainer)` directly — never `loadTwitterWidget()`.

---

### `src/services/static_export.py` — `renderCarousel()` (to be modified)

**Analog:** Lines 1083–1120 of the same file

**Full existing function** (lines 1083–1120):
```javascript
function renderCarousel(results, idx) {
  const entry = results[idx];
  const post = allPosts[entry.id];
  const rs = reviewMap.get(entry.id) || null;
  const cardHtml = renderPost(post, rs);
  const total = results.length;
  const prevDisabled = idx === 0         ? 'disabled' : '';
  const nextDisabled = idx === total - 1 ? 'disabled' : '';
  const controlsOpen = document.getElementById('controls').classList.contains('controls-open');
  const optionsLabel = controlsOpen ? 'Options ▴' : 'Options ▾';
  const topNav = `<div id="carousel-top-nav">
    <button class="carousel-btn" id="carousel-top-prev" ${prevDisabled}>&larr; Prev</button>
    <button class="options-toggle-btn" id="carousel-options-toggle">${optionsLabel}</button>
    <button class="carousel-btn" id="carousel-top-next" ${nextDisabled}>Next &rarr;</button>
  </div>`;
  const nav = `<div id="carousel-nav">
    <button class="carousel-btn" id="carousel-prev" ${prevDisabled}>&larr; Prev</button>
    <span class="carousel-counter">${idx + 1} / ${total} posts</span>
    <button class="carousel-btn" id="carousel-next" ${nextDisabled}>Next &rarr;</button>
  </div>`;
  document.getElementById('post-list').innerHTML = topNav + cardHtml + nav;
  document.getElementById('carousel-top-prev').addEventListener('click', () => {
    if (carouselIndex > 0) { carouselIndex--; renderCarousel(results, carouselIndex); window.scrollTo(0, 0); }
  });
  document.getElementById('carousel-top-next').addEventListener('click', () => {
    if (carouselIndex < results.length - 1) { carouselIndex++; renderCarousel(results, carouselIndex); window.scrollTo(0, 0); }
  });
  document.getElementById('carousel-options-toggle').addEventListener('click', toggleOptions);
  document.getElementById('carousel-prev').addEventListener('click', () => {
    if (carouselIndex > 0) { carouselIndex--; renderCarousel(results, carouselIndex); window.scrollTo(0, 0); }
  });
  document.getElementById('carousel-next').addEventListener('click', () => {
    if (carouselIndex < results.length - 1) { carouselIndex++; renderCarousel(results, carouselIndex); window.scrollTo(0, 0); }
  });
  if (post.oembed_html) {
    loadTwitterWidget();
  }
}
```

**Modification points within this function:**

1. **Pool hit/miss branch** — replaces lines that compute `cardHtml` and assign `innerHTML`. Pool-miss path keeps the existing `innerHTML` assignment verbatim. Pool-hit path uses explicit `appendChild`:
   ```javascript
   // POOL HIT path replaces: const cardHtml = renderPost(post, rs); ... innerHTML = topNav + cardHtml + nav;
   const cardNode = prefetchPool.get(entry.id);
   prefetchPool.delete(entry.id);
   const t = document.createElement('div');
   t.innerHTML = topNav + '<div></div>' + nav;
   const topNavNode = t.children[0];
   const navNode    = t.children[2];
   const container  = document.getElementById('post-list');
   container.innerHTML = '';
   container.appendChild(topNavNode);
   container.appendChild(cardNode);
   container.appendChild(navNode);
   ```

2. **Warm-state check** — replaces the terminal `if (post.oembed_html) { loadTwitterWidget(); }` block (lines 1117–1119) on pool-hit path:
   ```javascript
   if (post.oembed_html && !cardNode.querySelector('blockquote.twitter-tweet')) {
     // Already warmed — skip loadTwitterWidget()
   } else if (post.oembed_html) {
     loadTwitterWidget();
   }
   ```
   Pool-miss path keeps the existing `loadTwitterWidget()` call unchanged.

3. **`schedulePrefetch` call** — add as last statement in the function body, after all event listeners and the `loadTwitterWidget` block:
   ```javascript
   schedulePrefetch(results, idx);
   ```

---

### `src/services/static_export.py` — `renderView()` carousel branch (to be modified)

**Analog:** Lines 1163–1208 of the same file

**Carousel branch** (lines 1188–1193):
```javascript
  if (currentMode === 'carousel') {
    if (carouselIndex >= results.length) carouselIndex = 0;
    cachedCarouselResults = results;
    renderCarousel(results, carouselIndex);
    return;
  }
```

**Modification:** Insert `clearPrefetchPool()` as the first statement inside the `if (currentMode === 'carousel')` block, before `renderCarousel()`:
```javascript
  if (currentMode === 'carousel') {
    clearPrefetchPool();                                   // NEW — D-09
    if (carouselIndex >= results.length) carouselIndex = 0;
    cachedCarouselResults = results;
    renderCarousel(results, carouselIndex);
    return;
  }
```

---

### `src/services/static_export.py` — New Prefetch Functions (add after `loadTwitterWidget`, before `renderOEmbedCard`)

**Analog insertion point:** After line 1033 (closing brace of `loadTwitterWidget`), before line 1035 (`renderOEmbedCard`).

**Pattern for new `_twitterWidgetLoaded` / `_twitterRenderedBound` guard** — already used in `loadTwitterWidget` (lines 1008–1014). New prefetch functions use the same `window.twttr && window.twttr.widgets` guard:
```javascript
if (window.twttr && window.twttr.widgets) {
  twttr.widgets.load(prefetchContainer);
}
```

**Pattern for `debounceTimer` cancellation + setTimeout** (lines 783, 1210–1213) — establishes the cancel-before-schedule idiom. `schedulePrefetch` follows the same shape but with `requestIdleCallback`/`cancelIdleCallback` as primary and `setTimeout`/`clearTimeout` as fallback:
```javascript
// Existing debounce pattern for reference shape:
let debounceTimer = null;
clearTimeout(debounceTimer);
debounceTimer = setTimeout(renderView, 150);
```

---

## Shared Patterns

### `let`/`const` variable declarations
**Source:** Lines 778–792 of `src/services/static_export.py`
**Apply to:** All new global prefetch variables (`PREFETCH_AHEAD`, `PREFETCH_BEHIND`, `prefetchPool`, `_prefetchContainer`, `_prefetchTimerId`)
**Pattern:** `const` for immutable config values; `let` for mutable state. `new Map()` for collections needing O(1) keyed lookup. `null` as sentinel for uninitialized references.

### Function declaration style
**Source:** Lines 974, 991, 1004, 1070, 1074, 1083, 1163 of `src/services/static_export.py`
**Apply to:** All four new prefetch functions (`_getPrefetchContainer`, `clearPrefetchPool`, `_runPrefetch`, `schedulePrefetch`)
**Pattern:** Named `function` declarations (not arrow functions), camelCase, private helpers prefixed with `_`.

### Guard-then-operate pattern
**Source:** Lines 1008–1015 of `src/services/static_export.py` (`loadTwitterWidget`)
**Apply to:** `_runPrefetch` twttr guard; `clearPrefetchPool` timer guard
**Pattern:**
```javascript
if (condition) {
  doThing();
}
```

### `_setupSkeletonFallback` — what NOT to replicate in prefetch path
**Source:** Lines 991–1002 and 1006 of `src/services/static_export.py`
**Apply to:** `_runPrefetch` — must call `twttr.widgets.load(prefetchContainer)` directly, never `loadTwitterWidget()`
**Reason:** `loadTwitterWidget` calls `document.querySelectorAll('.oembed-container').forEach(_setupSkeletonFallback)` which starts 5-second timers for every oembed-container in the document, including hidden prefetch nodes.

---

## Test Pattern

### `tests/test_static_export_service.py` — `TestIndexHtmlCarousel` and `TestIndexHtmlDeepLink`

**Analog:** Lines 248–351 and 354+ of the same file

**Canonical test structure** (lines 248–257, 267–274):
```python
class TestIndexHtmlCarousel:
    """Tests for carousel mode additions to index.html. VIEWER-01 through VIEWER-05."""

    def test_mode_switcher_button_class_present(self, temp_db_v6, tmp_path):
        """VIEWER-01: mode switcher button class present in generated HTML."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "mode-btn" in html

    def test_carousel_render_function_present(self, temp_db_v6, tmp_path):
        """VIEWER-03: renderCarousel function and carouselIndex variable present."""
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "renderCarousel" in html
        assert "carouselIndex" in html
```

**New `TestIndexHtmlPrefetch` follows identical shape** — same fixture pair (`temp_db_v6, tmp_path`), same inline import, same `svc.export(tmp_path)` + `read_text()` + `assert "identifier" in html` structure. Class docstring references PREFETCH-08.

**Multi-assertion variant** (lines 267–274) — single test may assert multiple related identifiers:
```python
assert "renderCarousel" in html
assert "carouselIndex" in html
```

**Identifiers to assert per requirement:**
| Req | Assert |
|-----|--------|
| PREFETCH-01 | `"schedulePrefetch" in html` |
| PREFETCH-02 | `"PREFETCH_BEHIND" in html` |
| PREFETCH-04 | `"requestIdleCallback" in html` |
| PREFETCH-05 | `"prefetchPool.has" in html` |
| PREFETCH-06 | `"clearPrefetchPool" in html` |
| PREFETCH-07 | `"prefetchPool.delete" in html` |
| PREFETCH-08 | `"prefetchPool" in html` (covered by above) |

---

## No Analog Found

None. All patterns derive from the existing inline JS and test class structure within the two modified files.

---

## Metadata

**Analog search scope:** `src/services/static_export.py` (lines 777–1260), `tests/test_static_export_service.py` (lines 248–451)
**Files scanned:** 3 (`static_export.py`, `test_static_export_service.py`, `tests/conftest.py`)
**Pattern extraction date:** 2026-07-18
