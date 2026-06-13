# Phase 16: Viewer Presentation Modes - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 2 (1 modified source file + 1 new/extended test file)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/services/static_export.py` (`_build_index_html()`) | service (HTML generator) | transform (Python string → HTML/CSS/JS) | itself — extending existing method | exact (in-place extension) |
| `tests/test_static_export_service.py` (`TestIndexHtmlCarousel`) | test | request-response (string-grep assertions) | `TestIndexHtml` class (lines 186–246, same file) | exact |

---

## Pattern Assignments

### `src/services/static_export.py` — `_build_index_html()` (lines 333–892)

This is the only file modified. All insertions are additive within the returned HTML/CSS/JS string.

---

#### Insertion Point 1: CSS additions (after line 534, before `</style>`)

**Analog:** Existing CSS blocks in the same string — e.g., `#header` block (lines 383–400) and `.pill` block (lines 469–476).

**Pattern to copy — button with active state** (lines 469–476):
```css
/* src/services/static_export.py lines 469–476 */
.pill {
  display: inline-block;
  background: var(--color-accent);
  color: #fff; font-size: 13px; font-weight: 400;
  padding: var(--xs) var(--sm);
  border-radius: 12px; line-height: 1.4;
}
```
Mode switcher buttons follow the same `border-radius: 12px` pill shape, same spacing tokens, same `--color-accent` fill for the active state.

**New CSS to add — `.mode-switcher`, `.mode-btn`, `#carousel-nav`:**
```css
/* ADD after line 534 (before </style>) */
/* -- Mode switcher (pill group in header) -- */
.mode-switcher {
  display: flex; margin-left: auto; gap: 2px;
}
.mode-btn {
  background: transparent;
  color: var(--color-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: var(--xs) var(--md);
  font-size: 13px; font-weight: 500;
  cursor: pointer; transition: none;
}
.mode-btn.active {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}
/* -- Carousel nav controls -- */
#carousel-nav {
  display: flex; align-items: center; justify-content: center;
  gap: var(--lg); margin-top: var(--lg);
}
.carousel-btn {
  background: transparent;
  color: var(--color-link);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--xs) var(--md);
  font-size: 14px; cursor: pointer;
}
.carousel-btn:disabled {
  opacity: 0.3; cursor: not-allowed; pointer-events: none;
}
.carousel-counter {
  font-size: 14px; color: var(--color-secondary);
}
```

**CSS variables available** (lines 343–364):
```css
/* src/services/static_export.py lines 343–364 */
--color-bg:        #0f172a;
--color-card:      #1e293b;
--color-accent:    #2563eb;
--color-border:    #334155;
--color-text:      #f1f5f9;
--color-secondary: #94a3b8;
--color-muted:     #64748b;
--color-link:      #60a5fa;
/* Spacing tokens: --xs:4px  --sm:8px  --md:16px  --lg:24px */
```

---

#### Insertion Point 2: HTML additions (lines 539–542, `#header` block)

**Existing `#header` HTML** (lines 539–542):
```html
<!-- src/services/static_export.py lines 539–542 -->
<div id="header">
  <h1>X Bookmarks</h1>
  <span id="count-badge">...</span>
</div>
```
`#header` is a flex row (`display: flex; align-items: center; gap: var(--sm)` — line 389). Use `margin-left: auto` on `.mode-switcher` to push it to the right edge.

**New HTML to add — mode switcher buttons after `#count-badge`:**
```html
<!-- REPLACE lines 539–542 -->
<div id="header">
  <h1>X Bookmarks</h1>
  <span id="count-badge">...</span>
  <div class="mode-switcher">
    <button class="mode-btn active" data-mode="stream" onclick="setMode('stream')">Stream</button>
    <button class="mode-btn" data-mode="carousel" onclick="setMode('carousel')">Carousel</button>
  </div>
</div>
```

---

#### Insertion Point 3: JS global state variables (after line 616, existing globals block)

**Existing global state** (lines 610–616):
```javascript
// src/services/static_export.py lines 610–616
let allPosts = {};
let searchIndex = [];
let reviewMap = new Map();
let totalPostCount = 0;
let exportedDate = '';
let debounceTimer = null;
```

**New globals to add immediately after line 616:**
```javascript
// ADD after line 616
let currentMode = localStorage.getItem('xbm_mode') || 'stream';
let carouselIndex = 0;
let savedScrollY = 0;
```

---

#### Insertion Point 4: New JS functions (after `renderPost()` at line 795, before `showError()` at line 797)

**Existing `renderPost()` — the function carousel reuses unchanged** (lines 789–795):
```javascript
// src/services/static_export.py lines 789–795
function renderPost(post, reviewState) {
  if (post.oembed_html) return renderOEmbedCard(post, reviewState);
  const type = post.post_type || 'original';
  if (type === 'retweet') return renderRetweetCard(post, reviewState);
  if (type === 'quote')   return renderQuoteCard(post, reviewState);
  return renderOriginalCard(post, reviewState);
}
```

**oEmbed re-render pattern to mirror in `renderCarousel()`** (lines 851–856):
```javascript
// src/services/static_export.py lines 851–856
if (results.some(e => allPosts[e.id] && allPosts[e.id].oembed_html)) {
  loadTwitterWidget();
  if (window.twttr && window.twttr.widgets) {
    window.twttr.widgets.load(container);
  }
}
```
In `renderCarousel()`, replace `container` with `document.getElementById('post-list')` and check `post.oembed_html` directly (single post, not `.some()`).

**New functions to add between line 795 and line 797:**
```javascript
// ADD after renderPost() (line 795)

function setMode(mode) {
  if (mode === currentMode) return;
  if (mode === 'carousel') { savedScrollY = window.scrollY; }
  if (mode === 'stream')   { requestAnimationFrame(() => window.scrollTo(0, savedScrollY)); }
  currentMode = mode;
  localStorage.setItem('xbm_mode', mode);
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  renderView();
}

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
  document.getElementById('carousel-prev').addEventListener('click', () => {
    if (carouselIndex > 0) { carouselIndex--; renderView(); window.scrollTo(0, 0); }
  });
  document.getElementById('carousel-next').addEventListener('click', () => {
    if (carouselIndex < results.length - 1) { carouselIndex++; renderView(); window.scrollTo(0, 0); }
  });
  if (post.oembed_html) {
    loadTwitterWidget();
    if (window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(document.getElementById('post-list'));
    }
  }
}
```

---

#### Insertion Point 5: `renderView()` modification (lines 818–857)

**Existing `renderView()` — full body** (lines 818–857):
```javascript
// src/services/static_export.py lines 818–857
function renderView() {
  const results = filterAndSort();
  const filtered = results.length;
  const total = totalPostCount;
  const badge = filtered === total
    ? `${total} posts`
    : `${filtered} of ${total} posts`;
  document.getElementById('count-badge').textContent = badge;

  const container = document.getElementById('post-list');
  const emptyEl = document.getElementById('empty-state');
  emptyEl.style.display = 'none';

  if (total === 0) {
    showEmptyState('no_posts');
    container.innerHTML = '';
    return;
  }
  if (filtered === 0) {
    showEmptyState('no_results');
    container.innerHTML = '';
    return;
  }

  container.innerHTML = results
    .map(entry => {
      const post = allPosts[entry.id];
      if (!post) return '';
      const rs = reviewMap.get(entry.id) || null;
      return renderPost(post, rs);
    })
    .join('');

  if (results.some(e => allPosts[e.id] && allPosts[e.id].oembed_html)) {
    loadTwitterWidget();
    if (window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(container);
    }
  }
}
```

**Modified `renderView()` — replace lines 818–857 entirely:**
```javascript
// REPLACE renderView() at lines 818–857
function renderView() {
  const results = filterAndSort();
  const filtered = results.length;
  const total = totalPostCount;
  const badge = filtered === total
    ? `${total} posts`
    : `${filtered} of ${total} posts`;
  document.getElementById('count-badge').textContent = badge;

  const container = document.getElementById('post-list');
  const emptyEl = document.getElementById('empty-state');
  emptyEl.style.display = 'none';

  if (total === 0) {
    showEmptyState('no_posts');
    container.innerHTML = '';
    return;
  }
  if (filtered === 0) {
    showEmptyState('no_results');
    container.innerHTML = '';
    return;
  }

  if (currentMode === 'carousel') {
    carouselIndex = 0;  // reset on every renderView call in carousel mode
    renderCarousel(results, carouselIndex);
    return;
  }

  // Stream mode (original path — unchanged)
  container.innerHTML = results
    .map(entry => {
      const post = allPosts[entry.id];
      if (!post) return '';
      const rs = reviewMap.get(entry.id) || null;
      return renderPost(post, rs);
    })
    .join('');

  if (results.some(e => allPosts[e.id] && allPosts[e.id].oembed_html)) {
    loadTwitterWidget();
    if (window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(container);
    }
  }
}
```

---

#### Insertion Point 6: Keyboard listener (after line 865, in event listener block)

**Existing event listener block** (lines 859–865):
```javascript
// src/services/static_export.py lines 859–865
// -- Event listeners --
document.getElementById('search-input').addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderView, 150);
});
document.getElementById('date-filter').addEventListener('change', renderView);
document.getElementById('sort-order').addEventListener('change', renderView);
```

**New keyboard listener to add after line 865:**
```javascript
// ADD after line 865
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

---

#### CSS: `#main` max-width in carousel mode

**Existing `#main` block** (lines 423–427):
```css
/* src/services/static_export.py lines 423–427 */
#main {
  max-width: 720px; margin: 0 auto;
  padding: var(--xl) var(--md);
}
```
Carousel posts use `860px` max-width (wider than stream's `720px`). Add a body class toggle or override `#post-list` in carousel mode via CSS. Simplest approach: add `.carousel-mode #main { max-width: 860px; }` and toggle `document.body.classList.toggle('carousel-mode', mode === 'carousel')` inside `setMode()`.

---

### `tests/test_static_export_service.py` — `TestIndexHtmlCarousel` (new class)

**Analog:** `TestIndexHtml` class (lines 186–246, same file).

**Existing test class pattern** (lines 186–228):
```python
# tests/test_static_export_service.py lines 186–228
class TestIndexHtml:
    """Tests for index.html content. EXPORT-02."""

    def test_index_html_contains_fetch_calls(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "fetch('search-index.json')" in html

    def test_index_html_contains_esc_helper(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "function esc(" in html
```

**New test class to add after `TestIndexHtml` (after line 246):**
```python
# ADD after TestIndexHtml class (line 246)
class TestIndexHtmlCarousel:
    """Tests for carousel mode additions to index.html. VIEWER-01 through VIEWER-05."""

    def test_mode_switcher_button_class_present(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "mode-btn" in html

    def test_localstorage_key_present(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "xbm_mode" in html

    def test_carousel_render_function_present(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "renderCarousel" in html
        assert "carouselIndex" in html

    def test_keyboard_nav_listener_present(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "ArrowRight" in html
        assert "ArrowLeft" in html
        assert "Escape" in html

    def test_carousel_nav_dom_ids_present(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "carousel-nav" in html
        assert "carousel-prev" in html
        assert "carousel-next" in html
        assert "carousel-counter" in html

    def test_oembed_reinit_called_in_carousel(self, temp_db_v6, tmp_path):
        from src.services.static_export import StaticExportService
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)
        html = (tmp_path / "index.html").read_text()
        assert "twttr.widgets.load" in html
```

---

## Shared Patterns

### HTML Escaping
**Source:** `src/services/static_export.py` lines 583–590 (`esc()` function)
**Apply to:** Any new carousel template strings that include dynamic content
```javascript
// src/services/static_export.py lines 583–590
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
```
The carousel calls `renderPost()` which already uses `esc()` internally. The only new dynamic content in carousel HTML is the counter `${idx + 1} / ${total} posts` — these are numeric, no escaping needed.

### oEmbed Widget Initialization
**Source:** `src/services/static_export.py` lines 770–779 + 851–856
**Apply to:** `renderCarousel()` after setting `innerHTML`
```javascript
// src/services/static_export.py lines 770–779
let _twitterWidgetLoaded = false;
function loadTwitterWidget() {
  if (_twitterWidgetLoaded) return;
  _twitterWidgetLoaded = true;
  const s = document.createElement('script');
  s.src = 'https://platform.twitter.com/widgets.js';
  s.async = true;
  s.charset = 'utf-8';
  document.head.appendChild(s);
}
// lines 851–856
if (results.some(e => allPosts[e.id] && allPosts[e.id].oembed_html)) {
  loadTwitterWidget();
  if (window.twttr && window.twttr.widgets) {
    window.twttr.widgets.load(container);
  }
}
```

### CSS Variables Design System
**Source:** `src/services/static_export.py` lines 343–364
**Apply to:** All new CSS rules for `.mode-switcher`, `.mode-btn`, `#carousel-nav`, `.carousel-btn`
Use `--color-accent` (active fill), `--color-border` (inactive borders), `--color-secondary` (muted text), `--color-link` (nav button text), spacing tokens `--xs/--sm/--md/--lg`.

### Test Fixture
**Source:** `tests/conftest.py` fixture `temp_db_v6` (line 435) + `tmp_path` (pytest built-in)
**Apply to:** All `TestIndexHtmlCarousel` methods — identical fixture signature as `TestIndexHtml`
```python
# tests/conftest.py line 435
@pytest.fixture
def temp_db_v6(temp_db_v5):
    # Yields sqlite3.Connection with v6 schema + seed data
    ...
```

---

## No Analog Found

None. Every file has a direct analog in the codebase.

---

## Critical Anti-Patterns (from RESEARCH.md)

These are coding errors to avoid — confirmed by direct codebase inspection:

| Anti-Pattern | Why Dangerous | Correct Pattern |
|---|---|---|
| Place `document.addEventListener('keydown', ...)` inside `renderView()` | Creates N duplicate listeners after N renders | Add once at lines 859–865 event listener block |
| Call `filterAndSort()` inside `renderCarousel()` | Double-computes per render (already called by `renderView()`) | Pass `results` as parameter: `renderCarousel(results, idx)` |
| Call `twttr.widgets.load(document.body)` | Re-renders all widgets on page | Pass scoped container: `twttr.widgets.load(document.getElementById('post-list'))` |
| Skip `pointer-events: none` on disabled buttons | Opacity-0.3 buttons remain clickable | Include `pointer-events: none` in `.carousel-btn:disabled` |
| Access `results[carouselIndex]` without resetting on filter change | Out-of-bounds after result set shrinks | Reset `carouselIndex = 0` at top of carousel branch in `renderView()` |

---

## Metadata

**Analog search scope:** `src/services/static_export.py` (single-file phase), `tests/test_static_export_service.py`, `tests/conftest.py`
**Files scanned:** 3
**Pattern extraction date:** 2026-06-13
