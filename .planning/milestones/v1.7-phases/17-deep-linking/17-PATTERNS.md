# Phase 17: Deep Linking — Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 2 (1 modified implementation file + 1 modified test file)
**Analogs found:** 2 / 2 (both files are being modified; patterns extracted from the same files)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/services/static_export.py` | service (inline HTML/JS generator) | request-response (static build) | self — existing patterns within `_build_index_html()` | exact |
| `tests/test_static_export_service.py` | test | request-response (string-grep) | `TestIndexHtmlCarousel` class (lines 248–351) | exact |

---

## Pattern Assignments

### `src/services/static_export.py` — Five integration points within `_build_index_html()`

This file contains all CSS, HTML, and JS as a single Python triple-quoted string. All new deep-link code is an additive edit to that string. Five distinct sub-patterns apply.

---

#### Integration Point 1: Global state flag — `let deepLinkMode = false`

**Analog:** Global state block (lines 722–736)

**Pattern** (lines 722–736):
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
document.body.classList.toggle('carousel-mode', currentMode === 'carousel');
```

**Instruction:** Add `let deepLinkMode = false;` immediately after the last `let` declaration in this block (after line 732, before line 733). Match the indentation and `let` keyword style exactly.

---

#### Integration Point 2: `renderCardFooter()` — share icon + `copyDeepLink()` function

**Analog:** `renderCardFooter` (lines 845–850) and `renderOriginalCard` call pattern (lines 859–868)

**Existing `renderCardFooter` to be modified** (lines 845–850):
```javascript
function renderCardFooter(post) {
  const url = `https://x.com/i/web/status/${esc(post.x_post_id)}`;
  return `<div class="card-footer">
    <a href="${url}" target="_blank" rel="noopener noreferrer" class="view-on-x">View on X</a>
  </div>`;
}
```

**CSS anchor for card footer style** (lines 539–545):
```css
/* -- Card footer: View on X -- */
.card-footer { display: flex; justify-content: flex-end; margin-top: var(--sm); }
.view-on-x {
  color: var(--color-link); font-size: 13px; font-weight: 400;
  text-decoration: none;
}
.view-on-x:hover { text-decoration: underline; }
```

**`esc()` pattern for user content in onclick/href** (lines 696–702):
```javascript
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
```

**Instruction:** Replace `renderCardFooter` body so the `.card-footer` div contains both a share `<button>` and the existing "View on X" `<a>`. Add `copyDeepLink(postId, btnId)` as a new sibling function immediately after `renderCardFooter`. New CSS classes `share-btn` go in the CSS block near `.view-on-x` (after line 545) to match the 13px muted footer style. Always pass `post.x_post_id` through `esc()` in onclick attribute and button id.

**oEmbed pitfall:** `renderOEmbedCard` (lines 906–912) currently does NOT call `renderCardFooter`. All three other card renderers do (lines 866, 877, 890). Add `renderCardFooter(post)` call to `renderOEmbedCard` so the share icon appears on oEmbed cards per D-08.

```javascript
// renderOEmbedCard current (lines 906-912) — missing renderCardFooter:
function renderOEmbedCard(post, reviewState) {
  return `<div class="post-card oembed-card">
    <div class="oembed-container">${post.oembed_html}</div>
    ${renderPillsRow(post.tags, post.topics)}
    ${renderReviewBadge(reviewState)}
  </div>`;
}
```

---

#### Integration Point 3: Header HTML — "XBM Home" button + CSS visibility

**Analog:** `body.carousel-mode` CSS class toggle pattern — CSS at line 441 and JS at lines 931, 733

**Header HTML block** (lines 637–646 — the section being modified):
```html
<div id="header-wrapper">
<div id="header">
  <h1>X Bookmarks</h1>
  <span id="count-badge">...</span>
  <div class="mode-switcher">
    <button class="mode-btn active" data-mode="carousel" onclick="setMode('carousel')">Carousel</button>
    <button class="mode-btn" data-mode="stream" onclick="setMode('stream')">Stream</button>
  </div>
  <button class="options-toggle-btn" id="header-options-btn" onclick="toggleOptions()">Options ▾</button>
</div>
```

**CSS model for conditional visibility** (lines 441, 452–453):
```css
.carousel-mode #header-options-btn { display: none; }
.carousel-mode #controls { display: none; }
.carousel-mode #controls.controls-open { display: flex; }
```

**JS model for classList toggle** (lines 731–733):
```javascript
document.body.classList.toggle('carousel-mode', currentMode === 'carousel');
```
And in `setMode()` (line 931):
```javascript
document.body.classList.toggle('carousel-mode', mode === 'carousel');
```

**Instruction:** Add `<a href="javascript:void(0)" id="xbm-home-btn" class="xbm-home-btn" onclick="goHome()">XBM Home</a>` inside `#header` alongside the existing `.mode-switcher`. Add CSS rules to the existing CSS block: `#xbm-home-btn { display: none; }` in the base styles; `body.deep-link-mode .mode-switcher { display: none !important; }` and `body.deep-link-mode #xbm-home-btn { display: inline-flex; ... }` matching the same specificity pattern used for `.carousel-mode` rules. Add `function goHome()` near `setMode()` (lines 922–933). The `document.body.classList.add('deep-link-mode')` call goes in the bootstrap handler (Integration Point 4).

---

#### Integration Point 4: Bootstrap hash detection — inside `Promise.all().then()` handler

**Analog:** The entire bootstrap block (lines 1101–1123)

**Existing bootstrap handler** (lines 1102–1123):
```javascript
Promise.all([
  fetch('search-index.json').then(r => { if (!r.ok) throw new Error('search-index.json: ' + r.status); return r.json(); }),
  fetch('posts.json').then(r => { if (!r.ok) throw new Error('posts.json: ' + r.status); return r.json(); }),
  fetch('tags.json').then(r => { if (!r.ok) throw new Error('tags.json: ' + r.status); return r.json(); }),
  fetch('topics.json').then(r => { if (!r.ok) throw new Error('topics.json: ' + r.status); return r.json(); }),
  fetch('review_state.json').then(r => { if (!r.ok) throw new Error('review_state.json: ' + r.status); return r.json(); }),
]).then(([indexData, postsData, tagsData, topicsData, reviewData]) => {
  searchIndex = indexData.entries || [];
  totalPostCount = postsData.post_count || 0;
  exportedDate = (postsData.exported_at || '').split('T')[0];

  (postsData.posts || []).forEach(p => { allPosts[p.x_post_id] = p; });
  reviewMap = new Map((reviewData.review_states || []).map(r => [r.post_id, r]));

  document.getElementById('footer').textContent =
    `Exported ${exportedDate} · ${totalPostCount} posts`;

  document.getElementById('loading').style.display = 'none';
  renderView();         // <-- hash detection goes HERE, before this line
}).catch(err => {
  showError(err.message || String(err));
});
```

**Instruction:** Insert hash detection block between line 1119 (`display = 'none'`) and line 1120 (`renderView()`). Use `allPosts[postId]` for O(1) lookup (populated at line 1113). Use `searchIndex.findIndex(e => e.id === postId)` for carousel position (array available at line 1109). Clear filter inputs by `document.getElementById('search-input').value = ''` etc. — element IDs are `search-input` (line 656), `date-filter` (line 660), `sort-order` (line 671).

**`showError()` model for `showDeepLinkError()`** (lines 986–993):
```javascript
function showError(message) {
  document.getElementById('loading').style.display = 'none';
  const el = document.getElementById('error-state');
  el.style.display = 'block';
  el.innerHTML = `<h2>Could not load bookmark data</h2>
    <p>Make sure you're viewing this file from Netlify, not by opening it directly. Direct file:// access does not support fetch().</p>
    <p style="color:var(--color-muted);font-size:13px;">${esc(message)}</p>`;
}
```

**Instruction:** Add `showDeepLinkError(postId)` immediately after `showError()`. It follows the identical pattern: hide `#loading`, show `#error-state`, set `innerHTML` with escaped content. The error message must use `esc(postId)` and include an "XBM Home" link (`<a href="..." class="view-on-x">XBM Home</a>`). URL built as `window.location.origin + window.location.pathname`.

---

#### Integration Point 5: `setMode()` — model for how mode activation works

**Analog:** `setMode()` (lines 922–933):
```javascript
function setMode(mode) {
  if (mode === currentMode) return;
  if (mode === 'carousel') { savedScrollY = window.scrollY; }
  if (mode === 'stream')   { requestAnimationFrame(() => window.scrollTo(0, savedScrollY)); }
  currentMode = mode;
  localStorage.setItem('xbm_mode', mode);
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  document.body.classList.toggle('carousel-mode', mode === 'carousel');
  renderView();
}
```

**Instruction:** Deep link init does NOT call `setMode()` — it directly sets `currentMode = 'carousel'`, writes `localStorage`, adds the body class, and calls `renderView()`. This avoids the early-return guard (`if (mode === currentMode) return`) which would silently skip initialization if the user was already in carousel mode.

---

### `tests/test_static_export_service.py` — `TestIndexHtmlDeepLink` class

**Analog:** `TestIndexHtmlCarousel` class (lines 248–351) — exact structural template

**Test stub pattern** (from lines 251–257 — canonical single test example):
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
```

**Exact setup sequence every test uses:**
1. `from src.services.static_export import StaticExportService` (local import inside method)
2. `svc = StaticExportService(temp_db_v6)` (fixture — already defined in conftest)
3. `svc.export(tmp_path)` (fixture — already defined)
4. `html = (tmp_path / "index.html").read_text()`
5. `assert "substring" in html` (simple substring grep — no HTML parsing)

**RED stub pattern** — before implementation, each test must fail with `AssertionError`. Since new strings won't be in the existing HTML, `assert "new-string" in html` is naturally RED on unmodified code. No special marking needed.

**Fixture used:** `temp_db_v6` — already available in conftest (used throughout `TestIndexHtmlCarousel`). No new fixtures required.

**New class to create** — 11 tests for requirements DL-01 through DL-11:

| Test method | String to assert | Req |
|---|---|---|
| `test_share_btn_present` | `"share-btn"` | DL-01 |
| `test_copy_deep_link_function_present` | `"copyDeepLink"` | DL-02 |
| `test_clipboard_write_present` | `"navigator.clipboard.writeText"` | DL-03 |
| `test_hash_detection_present` | `"window.location.hash"` | DL-04 |
| `test_post_hash_prefix_present` | `"#post-"` | DL-05 |
| `test_deep_link_mode_flag_present` | `"deepLinkMode"` | DL-06 |
| `test_deep_link_mode_css_class_present` | `"deep-link-mode"` | DL-07 |
| `test_xbm_home_btn_present` | `"xbm-home-btn"` | DL-08 |
| `test_go_home_function_present` | `"goHome"` | DL-09 |
| `test_show_deep_link_error_present` | `"showDeepLinkError"` | DL-10 |
| `test_xbm_home_text_present` | `"XBM Home"` | DL-11 |

Place the new `TestIndexHtmlDeepLink` class immediately after `TestIndexHtmlCarousel` (after line 351), before `TestNetlifyToml` (line 354).

---

## Shared Patterns

### `esc()` helper — must be applied everywhere
**Source:** `src/services/static_export.py` lines 696–702
**Apply to:** All new HTML string interpolations in new functions (`copyDeepLink`, `showDeepLinkError`, `renderCardFooter` share button)
**Rule:** Any value that originates from post data or user-controlled input (`post.x_post_id`, `postId` extracted from hash) must go through `esc()` before being placed in an `innerHTML` string.

### Body class toggle pattern — model for `body.deep-link-mode`
**Source:** `src/services/static_export.py` lines 733, 931
```javascript
document.body.classList.toggle('carousel-mode', currentMode === 'carousel');
// Deep link equivalent (one-way add, never removed during session):
document.body.classList.add('deep-link-mode');
```
**Apply to:** Bootstrap hash detection block. The `deep-link-mode` class is added once on page load if a deep link is detected; it is never removed (session flag).

### CSS conditional visibility pattern — `body.class selector { display: none; }`
**Source:** `src/services/static_export.py` lines 441, 452–453
```css
.carousel-mode #header-options-btn { display: none; }
.carousel-mode #controls { display: none; }
```
**Apply to:** New `body.deep-link-mode` CSS rules hiding `.mode-switcher` and `#header-options-btn`, showing `#xbm-home-btn`. Use same specificity: `body.deep-link-mode .mode-switcher { display: none !important; }`.

### Promise.all bootstrap — integration order constraint
**Source:** `src/services/static_export.py` lines 1102–1123
**Apply to:** Hash detection MUST be inside `.then()` handler, after line 1113 (`allPosts` is populated), before line 1120 (`renderView()`). Any hash detection placed at top-level JS (outside `.then()`) will see `allPosts = {}` and always fail lookup.

---

## No Analog Found

None — all patterns have direct analogs in the existing file.

---

## Metadata

**Analog search scope:** `src/services/static_export.py` and `tests/test_static_export_service.py`
**Files scanned:** 2 (both primary implementation and test file read in full)
**Pattern extraction date:** 2026-06-14
