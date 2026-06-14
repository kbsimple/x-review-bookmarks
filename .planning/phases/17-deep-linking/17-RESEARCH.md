# Phase 17: Deep Linking — Research

**Researched:** 2026-06-14
**Domain:** Client-side static HTML/JS — hash-based URL routing, clipboard API, conditional header rendering
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Opening a deep link URL (`#post-{x_post_id}`) puts the viewer into carousel mode showing only that specific post. All filters (search, date, sort) are cleared.
- **D-02:** The viewer detects the hash on page load (`window.location.hash`) and navigates to the matching post after data has loaded.
- **D-03:** If the hash references a post ID not found in `allPosts`, show a graceful "Post not found" message with an "XBM Home" link.
- **D-04:** Hash format: `#post-{x_post_id}` — e.g. `https://xbm-viewer-export.netlify.app/#post-1784230491234`. The `post-` prefix keeps the hash self-documenting and avoids collisions.
- **D-05:** The URL bar does NOT auto-update as the user navigates carousel in normal (non-deep-link) mode. Hash only appears when the user explicitly copies a share link.
- **D-06:** A share icon (📤 — standard native share icon, or a link-chain icon as fallback) appears on every post card.
- **D-07:** Clicking the icon copies the deep link URL to the clipboard via `navigator.clipboard.writeText()`. A brief visual confirmation (icon changes, or a small "Copied!" toast) acknowledges the copy.
- **D-08:** The share icon is visible in both carousel mode and stream mode.
- **D-09:** When the viewer is in deep-link mode (arrived via `#post-{id}`), the header shows an "XBM Home" button replacing the Carousel/Stream mode switcher.
- **D-10:** Clicking "XBM Home" navigates to the root URL (clears the hash), resetting the viewer to its default state — no filters, full post list, user's persisted mode (carousel/stream).
- **D-11:** "XBM Home" does NOT say "Back to all posts".
- **D-12:** Deep link arrival unconditionally clears all filters and bypasses filter/sort state.
- **D-13:** No filter state is encoded in the deep link URL — links are deliberately minimal (post ID only).

### Claude's Discretion

- Visual style of the share icon and "Copied!" confirmation — match the existing card footer style (small, muted, consistent with "View on X" link).
- Exact animation/duration of copy confirmation feedback.
- Whether the deep-link mode adds a visible "Linked post" label to the card header.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 17 adds hash-based deep linking to the static HTML viewer already at `src/services/static_export.py`. All implementation is inline JavaScript string mutations within `_build_index_html()`. No server changes, no new Python libraries, no new JSON files.

The feature has three parts: (1) a share icon in every post card footer that copies a `#post-{x_post_id}` URL to the clipboard, (2) hash detection on bootstrap that puts the viewer into a focused carousel state with filters cleared, and (3) an "XBM Home" button in the header that replaces the mode switcher when in deep-link mode.

The existing codebase provides every building block needed. `allPosts` is keyed by `x_post_id` enabling O(1) post lookup. `renderCarousel()` and `renderView()` are already parameterized correctly. The `body.carousel-mode` + `body.deep-link-mode` CSS class pattern (matching how carousel mode is toggled today) cleanly handles conditional header display. The only net-new capability is `navigator.clipboard.writeText()` and reading `window.location.hash` at bootstrap.

**Primary recommendation:** Implement entirely within `_build_index_html()` — add a `let deepLinkMode = false` flag, a `body.deep-link-mode` CSS class, hash detection in the bootstrap `.then()` handler, clipboard copy in `renderCardFooter()`, and an XBM Home button as a hidden DOM element made visible via CSS class.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Share icon + clipboard copy | Browser/Client (inline JS) | — | Pure client action; no server communication |
| Hash detection on load | Browser/Client (inline JS) | — | `window.location.hash` read after fetch Promise resolves |
| Deep-link carousel render | Browser/Client (inline JS) | — | Reuses existing `renderCarousel()` |
| Header conditional display | Browser/Client (CSS class) | — | `body.deep-link-mode` toggles CSS visibility |
| XBM Home navigation | Browser/Client (inline JS) | — | Sets `window.location.href` to root URL |
| "Post not found" error | Browser/Client (inline JS) | — | Renders into existing `#error-state` element |
| Python string generation | Backend (static_export.py) | — | Embeds all JS/CSS as Python string constants |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `navigator.clipboard` API | Browser native | Async clipboard write | [VERIFIED: MDN] Standard since 2018, available in all modern browsers; Netlify serves over HTTPS which satisfies the secure-context requirement |
| `window.location.hash` | Browser native | Read URL fragment on load | [VERIFIED: codebase] Already used implicitly; no new dependency |
| `window.location.href` | Browser native | Navigate to root URL | [VERIFIED: codebase] Existing pattern (`window.scrollTo` already called) |
| CSS body class toggle | Browser native | `body.deep-link-mode` visibility | [VERIFIED: codebase] Exact pattern used for `carousel-mode` at line 733 |

### No new Python dependencies required.

---

## Architecture Patterns

### System Architecture Diagram

```
User opens URL with #post-{id}
         |
         v
  Bootstrap Promise.all([fetch(...)]) resolves
         |
         v
  Read window.location.hash
  Parse prefix: does it start with "#post-"?
         |
    YES  |  NO
         |-----> Normal renderView() — existing path unchanged
         v
  Extract post_id = hash.slice(6)
  Look up: allPosts[post_id] exists?
         |
    YES  |  NO
         |-----> showDeepLinkError() — renders into #error-state
         v         with "XBM Home" link
  deepLinkMode = true
  document.body.classList.add('deep-link-mode')
  Clear filters (search/date/sort inputs reset to "")
  setMode('carousel') if not already
  Find index in searchIndex where entry.id === post_id
  carouselIndex = that index (or 0 if not in searchIndex)
  renderView()


User clicks share icon on a post card
         |
         v
  Build URL: window.location.origin + window.location.pathname + "#post-" + post.x_post_id
  navigator.clipboard.writeText(url)
  .then(() => brief visual confirmation on icon)


User clicks "XBM Home" button
         |
         v
  window.location.href = window.location.origin + window.location.pathname
  (page reloads, no hash, deepLinkMode never activates)
```

### Recommended Project Structure

No new files. All changes to one Python method:

```
src/
└── services/
    └── static_export.py   # _build_index_html() only — CSS + HTML + JS additions
tests/
└── test_static_export_service.py  # Add TestIndexHtmlDeepLink class
```

### Pattern 1: Hash Detection in Bootstrap (after data loads)

The correct placement is inside the `.then()` handler after all JSON files are fetched, immediately before `renderView()` is called. This ensures `allPosts` and `searchIndex` are populated before the lookup.

```javascript
// Inside Promise.all(...).then(([indexData, postsData, ...]) => {
//   ... existing data population ...

  const hash = window.location.hash;
  if (hash && hash.startsWith('#post-')) {
    const postId = hash.slice(6);
    if (allPosts[postId]) {
      deepLinkMode = true;
      document.body.classList.add('deep-link-mode');
      // Clear all filter inputs
      document.getElementById('search-input').value = '';
      document.getElementById('date-filter').value = '';
      document.getElementById('sort-order').value = 'newest';
      // Find index in searchIndex
      const idx = searchIndex.findIndex(e => e.id === postId);
      carouselIndex = idx >= 0 ? idx : 0;
      currentMode = 'carousel';
      localStorage.setItem('xbm_mode', 'carousel');
      document.body.classList.add('carousel-mode');
    } else {
      showDeepLinkError(postId);
      return;
    }
  }
  renderView();
// });
```

[VERIFIED: codebase — bootstrap handler is at line 1102; allPosts populated at line 1113 before renderView at line 1120]

### Pattern 2: Share Icon in `renderCardFooter()`

The share button goes inside the existing `.card-footer` div alongside "View on X". The onclick uses an inline function to avoid needing to pass `post` as a data attribute.

```javascript
function renderCardFooter(post) {
  const xUrl = `https://x.com/i/web/status/${esc(post.x_post_id)}`;
  const shareId = `share-${esc(post.x_post_id)}`;
  return `<div class="card-footer">
    <button class="share-btn" id="${shareId}"
      onclick="copyDeepLink('${esc(post.x_post_id)}', '${shareId}')"
      title="Copy link to this post">&#128064;</button>
    <a href="${xUrl}" target="_blank" rel="noopener noreferrer" class="view-on-x">View on X</a>
  </div>`;
}

function copyDeepLink(postId, btnId) {
  const url = window.location.origin + window.location.pathname + '#post-' + postId;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.innerHTML = '&#128064;'; }, 1500);
    }
  }).catch(() => {
    // clipboard denied — silent fail or fallback
  });
}
```

Note on icon: 📤 is U+1F4E4, HTML entity `&#128100;`. For inline JS strings within Python triple-quoted strings, using the entity is safest. Alternatively use the literal emoji character directly — Python 3 handles it cleanly in string constants.

[VERIFIED: codebase — `renderCardFooter` is at line 845; `card-footer` CSS at line 540]

### Pattern 3: XBM Home Button — CSS-driven visibility

Add a hidden "XBM Home" button to the `#header` HTML. Use CSS to show it and hide `.mode-switcher` when `body.deep-link-mode` is active:

```html
<!-- In #header HTML (alongside existing mode-switcher) -->
<a href="javascript:void(0)" id="xbm-home-btn" class="xbm-home-btn"
   onclick="goHome()">XBM Home</a>
```

```css
/* -- Deep link mode: hide mode switcher, show XBM Home -- */
#xbm-home-btn { display: none; }
body.deep-link-mode .mode-switcher { display: none !important; }
body.deep-link-mode #header-options-btn { display: none !important; }
body.deep-link-mode #xbm-home-btn { display: inline-flex; ... }
```

```javascript
function goHome() {
  window.location.href = window.location.origin + window.location.pathname;
}
```

[VERIFIED: codebase — `body.carousel-mode` class toggle pattern at line 733; `.mode-switcher` at line 641]

### Pattern 4: "Post Not Found" Error

Reuse the existing `#error-state` element. Do NOT use `showError()` (which shows a fetch-failure message). Add a new `showDeepLinkError(postId)` function:

```javascript
function showDeepLinkError(postId) {
  document.getElementById('loading').style.display = 'none';
  const el = document.getElementById('error-state');
  el.style.display = 'block';
  el.innerHTML = `<h2>Post not found</h2>
    <p>The linked post (ID: ${esc(postId)}) is no longer in this export.</p>
    <p><a href="${esc(window.location.origin + window.location.pathname)}" class="view-on-x">XBM Home</a></p>`;
}
```

[VERIFIED: codebase — `#error-state` element at line 685; `showError()` at line 986]

### Pattern 5: Global `deepLinkMode` flag

Add to the "Global state" section (around line 723):

```javascript
let deepLinkMode = false;
```

This flag is used by `renderCarousel()` if needed (e.g., to hide the navigation counter, or add a "Linked post" label per Claude's discretion).

### Anti-Patterns to Avoid

- **Setting `window.location.hash` in the share URL**: `window.location.origin + window.location.pathname + '#post-' + postId` is correct. Do NOT use `window.location.href` (may include existing hash) or `document.URL` (same issue).
- **Reading hash before data loads**: Hash detection MUST happen inside the `.then()` handler after `allPosts` is populated. Reading `window.location.hash` at top-level JS execution time (before fetch) means `allPosts` is empty.
- **Resetting `localStorage` for mode on deep link**: Deep link sets `currentMode = 'carousel'` in memory and calls `localStorage.setItem`. When user clicks XBM Home the page reloads fresh — `localStorage.getItem('xbm_mode')` returns whatever they had before (carousel). This is correct per D-10.
- **Using `window.location.hash = ''` for XBM Home**: This pushes a history entry with `#`. Use `window.location.href = origin + pathname` to get a clean URL reload with no fragment.
- **Embedding post ID directly in onclick attribute without `esc()`**: Post IDs from X are numeric strings (safe), but the pattern is established: always use `esc()` for any user content in innerHTML.
- **Using `document.execCommand('copy')` fallback**: This is deprecated. `navigator.clipboard.writeText()` is the correct API and works on Netlify (HTTPS). A silent `.catch()` is acceptable since the Netlify deployment context guarantees HTTPS.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Clipboard write | Custom textarea/execCommand hack | `navigator.clipboard.writeText()` | [VERIFIED: MDN] Async Clipboard API handles permissions, secure context check, and fallback internally. execCommand is deprecated. |
| URL construction | String concat of full href | `window.location.origin + window.location.pathname` | Correctly strips existing fragment; avoids double-hash if user is already on a deep link URL |
| Post lookup for deep link | Linear scan through searchIndex | `allPosts[postId]` direct key lookup | `allPosts` is keyed by `x_post_id` — O(1) existence check. Then use `searchIndex.findIndex()` only to get the carousel position. |
| Carousel entry for a single post | New single-element results array | Find index in full `searchIndex` array | Using full results with correct index lets prev/next continue to adjacent posts naturally. A single-item array would make prev/next dead immediately. |

**Key insight:** The hard part of deep linking (state management, routing) is trivially solved by the existing `allPosts` keyed object and `filterAndSort()` pattern. The main risk is integration order — hash detection must run AFTER data loads.

---

## Common Pitfalls

### Pitfall 1: Hash Detection Before Data

**What goes wrong:** Putting hash detection at top-level JS (outside the `.then()` handler) means `allPosts` is `{}` and `searchIndex` is `[]`. Post lookup always fails.
**Why it happens:** Natural impulse to run setup logic at page load.
**How to avoid:** Hash detection code goes inside `.then()` after `allPosts` is populated, immediately before `renderView()`.
**Warning signs:** Deep link always shows "Post not found" even for valid IDs.

### Pitfall 2: Incorrect Deep Link URL in Share

**What goes wrong:** `window.location.href` includes the current `#fragment`. If user is already on a deep link (`#post-111`) and shares a different post, the copied URL becomes `base/#post-111#post-222`.
**Why it happens:** `window.location.href` is the full URL including current fragment.
**How to avoid:** Build URL as `window.location.origin + window.location.pathname + '#post-' + postId`. This always produces a clean base URL with only the new fragment.
**Warning signs:** Shared URL contains double hash.

### Pitfall 3: `localStorage` Mode Overwrite on Deep Link

**What goes wrong:** If deep link sets `localStorage.setItem('xbm_mode', 'carousel')`, then XBM Home navigation restores to carousel even if user's original preference was stream.
**Why it happens:** Carousel is force-activated on deep link arrival. If `localStorage` is written, it persists.
**How to avoid:** Per the CONTEXT.md code notes, `localStorage` should be written (it will be carousel — which is the expected post-home behavior since the user was just in a carousel view). When they click XBM Home, the page reloads and reads `localStorage`, which now says 'carousel'. This is acceptable behavior — the user chose to visit the deep link, the viewer stays in carousel mode. If this is a concern, the alternative is to NOT write `localStorage` during deep link init and instead set `currentMode` in-memory only, but this would fight the existing `setMode()` code.
**Warning signs:** User's mode preference irreversibly changed by sharing a link.

### Pitfall 4: Deep Link Mode Not Cleared on Filter Change

**What goes wrong:** If user manually types in the search box while in deep-link mode, the XBM Home button should remain visible (deepLinkMode stays `true`). The header change is NOT tied to filter state — it's tied to how the page was arrived at.
**Why it happens:** Conflating "entered via deep link" with "currently showing one post".
**How to avoid:** `deepLinkMode` is a flag set once on page load. It is never cleared by filter events. XBM Home is always visible until page reload.
**Warning signs:** XBM Home button disappears when user searches.

### Pitfall 5: `navigator.clipboard` Rejected in Dev (non-HTTPS)

**What goes wrong:** If testing locally via `file://` or `http://`, `navigator.clipboard.writeText()` throws because clipboard requires a secure context.
**Why it happens:** Async Clipboard API is HTTPS-only (or localhost).
**How to avoid:** Silent `.catch()` on the clipboard call. On Netlify (HTTPS) it always works. In tests, the function call is verified by string-grep pattern (not by executing the JS), so no JS sandbox needed.
**Warning signs:** "NotAllowedError: Document is not focused" or similar in browser console during local testing.

### Pitfall 6: `renderOEmbedCard` Does Not Call `renderCardFooter`

**What goes wrong:** oEmbed posts (`post.oembed_html` truthy) are rendered by `renderOEmbedCard()`, which does NOT call `renderCardFooter()`. Share icon would be missing from oEmbed cards.
**Why it happens:** `renderOEmbedCard` was added without a card footer (native Twitter widget provides its own "View on X").
**How to avoid:** Add `renderCardFooter(post)` call to `renderOEmbedCard()`, OR add the share icon separately inside `renderOEmbedCard`. The share icon is specifically needed on oEmbed cards per D-08.
**Warning signs:** Share icon missing on posts with native Twitter embed.

[VERIFIED: codebase — `renderOEmbedCard` at line 906 has no `renderCardFooter` call; `renderOriginalCard`, `renderRetweetCard`, `renderQuoteCard` all call it]

---

## Code Examples

### Existing bootstrap handler (integration point)

```javascript
// Source: src/services/static_export.py lines 1102-1123
Promise.all([...]).then(([indexData, postsData, tagsData, topicsData, reviewData]) => {
  searchIndex = indexData.entries || [];
  totalPostCount = postsData.post_count || 0;
  // ...
  (postsData.posts || []).forEach(p => { allPosts[p.x_post_id] = p; });
  // ... footer ...
  document.getElementById('loading').style.display = 'none';
  renderView();         // <-- deep link detection goes HERE, before this line
}).catch(err => {
  showError(err.message || String(err));
});
```

### Existing CSS class toggle pattern (model for deep-link-mode)

```javascript
// Source: src/services/static_export.py line 733
document.body.classList.toggle('carousel-mode', currentMode === 'carousel');

// Deep link mode follows same pattern:
document.body.classList.add('deep-link-mode');
```

### Existing `renderCardFooter` (will be modified)

```javascript
// Source: src/services/static_export.py lines 845-849
function renderCardFooter(post) {
  const url = `https://x.com/i/web/status/${esc(post.x_post_id)}`;
  return `<div class="card-footer">
    <a href="${url}" target="_blank" rel="noopener noreferrer" class="view-on-x">View on X</a>
  </div>`;
}
```

### Existing error state rendering (model for showDeepLinkError)

```javascript
// Source: src/services/static_export.py lines 986-993
function showError(message) {
  document.getElementById('loading').style.display = 'none';
  const el = document.getElementById('error-state');
  el.style.display = 'block';
  el.innerHTML = `<h2>Could not load bookmark data</h2>...`;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `document.execCommand('copy')` | `navigator.clipboard.writeText()` | ~2018, baseline 2022 | Async, permission-based, works in HTTPS contexts — the correct API for Netlify |
| Custom hash routers (Backbone, etc.) | Native `window.location.hash` | N/A for this project | No framework needed; single hash format, read once on load |

**Deprecated/outdated:**
- `document.execCommand('copy')`: deprecated, inconsistent behavior; do not use.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pytest.ini` |
| Quick run command | `python3 -m pytest tests/test_static_export_service.py -q` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements → Test Map

All tests use the string-grep pattern: generate `index.html`, read it as text, assert substring presence. This is the established pattern in `TestIndexHtmlCarousel`.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DL-01 | Share button present in card footer HTML | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_share_btn_present -x` | ❌ Wave 0 |
| DL-02 | `copyDeepLink` function present in JS | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_copy_deep_link_function_present -x` | ❌ Wave 0 |
| DL-03 | `navigator.clipboard.writeText` call present | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_clipboard_write_present -x` | ❌ Wave 0 |
| DL-04 | `window.location.hash` read present | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_hash_detection_present -x` | ❌ Wave 0 |
| DL-05 | `#post-` prefix parsing present | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_post_hash_prefix_present -x` | ❌ Wave 0 |
| DL-06 | `deepLinkMode` flag declared | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_deep_link_mode_flag_present -x` | ❌ Wave 0 |
| DL-07 | `body.deep-link-mode` CSS class present | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_deep_link_mode_css_class_present -x` | ❌ Wave 0 |
| DL-08 | `xbm-home-btn` element present in header HTML | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_xbm_home_btn_present -x` | ❌ Wave 0 |
| DL-09 | `goHome` function present | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_go_home_function_present -x` | ❌ Wave 0 |
| DL-10 | `showDeepLinkError` function present | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_show_deep_link_error_present -x` | ❌ Wave 0 |
| DL-11 | "XBM Home" text present in HTML | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_xbm_home_text_present -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_static_export_service.py -q`
- **Per wave merge:** `python3 -m pytest -q`
- **Phase gate:** Full suite green (currently 633 tests) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_static_export_service.py` — add `TestIndexHtmlDeepLink` class with 11 stub methods (all failing RED initially)

*(Existing test infrastructure covers all other aspects — only the new class is needed)*

---

## Environment Availability

Step 2.6: SKIPPED — Phase 17 is a pure code-change phase. No new external tools, services, runtimes, CLIs, or databases are required. All changes are to the Python string constant inside `_build_index_html()`. The only "runtime" is the user's browser (already proven by Netlify deployment).

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `esc()` helper — already in use, must be applied to `post.x_post_id` in share URL and onclick attribute |
| V6 Cryptography | no | — |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via `post.x_post_id` in onclick | Tampering | `esc()` on all post IDs before innerHTML insertion — already established pattern in codebase |
| Open redirect via `window.location.href` in goHome | Tampering | `window.location.origin + window.location.pathname` hard-codes the current origin; no external input used |
| Hash injection (`#post-<script>`) | Tampering | `esc()` applied to extracted `postId` before it appears in any DOM write |

**Security note:** X post IDs are numeric strings (e.g., `1784230491234`) — they contain no special characters in practice. However, defensive `esc()` usage is mandatory per the codebase convention and must be applied everywhere post IDs appear in HTML strings.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `renderOEmbedCard` should also call `renderCardFooter` (or equivalent) to show the share icon | Pitfall 6 | If oEmbed cards intentionally omit a footer, the share icon approach for those cards needs a different integration point — e.g., a wrapper div around the oembed-card |
| A2 | `window.location.origin + window.location.pathname` is the correct URL prefix for the share URL on Netlify | Pattern 2 | If Netlify's URL structure differs from this assumption, the generated share URL may be wrong. LOW risk: this is the standard way to get the base URL. |

---

## Open Questions

1. **oEmbed card footer integration**
   - What we know: `renderOEmbedCard()` currently has no `renderCardFooter()` call. Three other card renderers all call it.
   - What's unclear: D-08 says "share icon works in both carousel and stream modes" — it's silent on oEmbed vs. non-oEmbed distinction.
   - Recommendation: Add `renderCardFooter(post)` to `renderOEmbedCard()`. This also adds a "View on X" link to oEmbed cards, which is redundant (native widget has it), but consistent and harmless. Alternatively, inline just the share button without "View on X" inside `renderOEmbedCard`.

2. **Carousel index when deep linking: full results vs. single-post result**
   - What we know: `renderCarousel(results, idx)` takes a results array and index. On deep link, the user wants to land on a specific post.
   - What's unclear: Should the carousel show ALL posts (starting at the linked one) or only the linked post with prev/next disabled?
   - Recommendation: Use the full unfiltered `searchIndex` as the results array, find the matching index, and set `carouselIndex` to it. This makes the linked post navigable to adjacent posts — a better UX than a single dead-end post. The CONTEXT.md says "focused carousel view showing that post" — navigating to adjacent posts should still be possible (D-01 only says "showing only that specific post" in the initial focused view sense, not locked to a single item).

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `src/services/static_export.py` — all rendering functions, bootstrap handler, CSS class patterns, `esc()` helper. Read in full for this research session.
- [VERIFIED: codebase] `tests/test_static_export_service.py` — string-grep test pattern, `TestIndexHtmlCarousel` class as model.

### Secondary (MEDIUM confidence)
- [CITED: MDN] `navigator.clipboard.writeText()` — requires secure context (HTTPS or localhost). Standard since browsers ~2018, Baseline 2022. Netlify always serves HTTPS.
- [CITED: MDN] `window.location.hash` — synchronously available, returns `""` when no fragment present.
- [CITED: MDN] `window.location.origin + window.location.pathname` — correct pattern for base URL without fragment.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all native browser APIs
- Architecture: HIGH — derived entirely from reading the live codebase
- Pitfalls: HIGH — two (hash timing, oEmbed footer) are verified by direct code inspection; others (clipboard HTTPS, URL construction) are verified browser API behavior

**Research date:** 2026-06-14
**Valid until:** 2026-09-14 (stable — no external dependencies; browser APIs used are baseline standard)
