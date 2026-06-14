---
phase: 17-deep-linking
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tests/test_static_export_service.py
  - src/services/static_export.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the Phase 17 deep-linking additions: the `copyDeepLink()` JS function,
hash detection in the bootstrap block, `showDeepLinkError()`, `renderCardFooter()`
share button, `renderOEmbedCard()` patch, `goHome()`, CSS `.deep-link-mode` rules,
and the `TestIndexHtmlDeepLink` test class.

The implementation is largely correct. Hash detection timing is right (inside
`Promise.all().then()`). `showDeepLinkError()` uses `esc()` on the post ID.
`goHome()` strips the fragment cleanly. `renderOEmbedCard()` correctly includes
`renderCardFooter()`. The 11 DL-* test stubs follow the correct pattern.

Two issues need attention before shipping:

1. **CSS scoping bug (Warning):** `#xbm-home-btn` has no global `display: none`,
   so it is visible in the header on desktop at all times — not just in deep-link mode.
2. **Single-quote gap in onclick attributes (Warning):** `esc()` does not escape
   single quotes, so if a post ID ever contains `'`, the generated onclick attribute
   is syntactically broken. X post IDs are currently numeric, keeping actual risk low.

Two minor info items: the clipboard silent-fail catch has no user-visible fallback,
and there is no test asserting the XBM Home button is hidden outside deep-link mode
on desktop.

---

## Warnings

### WR-01: `#xbm-home-btn` always visible on desktop — CSS rule missing outside media query

**File:** `src/services/static_export.py:455` (generated CSS inside `@media (max-width: 600px)`)

**Issue:** The only CSS that sets `#xbm-home-btn { display: none; }` lives inside
`@media (max-width: 600px)`. On desktop (viewport > 600px), no rule hides the element
by default, so the "XBM Home" link is rendered visibly in the header for every visitor
on every page load — regardless of whether a `#post-` hash is in the URL.

The element at line 663 of the generated HTML:
```html
<a href="javascript:void(0)" id="xbm-home-btn" class="xbm-home-btn" onclick="goHome()">XBM Home</a>
```
has no corresponding global hide rule in the `<style>` block. The `.deep-link-mode`
show rules are also scoped to `@media (max-width: 600px)`, so on desktop the button is
always visible AND clicking it always navigates home.

**Fix:** Add a global (non-media-query) `display: none` for `#xbm-home-btn`, then
override it inside `.deep-link-mode` for all viewports:

```css
/* -- Deep link mode: XBM Home button (global, not mobile-only) -- */
#xbm-home-btn { display: none; }
body.deep-link-mode #xbm-home-btn {
  display: inline-flex; align-items: center;
  padding: 4px 12px; border-radius: 16px;
  background: var(--color-link); color: #fff;
  font-size: 13px; font-weight: 500; text-decoration: none;
  cursor: pointer;
}
body.deep-link-mode #xbm-home-btn:hover { opacity: 0.85; }
```

Remove the duplicate rules from inside `@media (max-width: 600px)`. The
`body.deep-link-mode .mode-switcher { display: none !important; }` rule may also
need to be promoted out of the mobile media query if deep-link mode should suppress
the mode switcher on desktop too.

---

### WR-02: `esc()` does not escape single quotes — onclick attributes vulnerable to breakage

**File:** `src/services/static_export.py:870-871` (generated `renderCardFooter` JS)

**Issue:** `esc()` escapes `&`, `<`, `>`, and `"` but not `'`. The `renderCardFooter`
function generates onclick attributes delimited by single quotes:

```js
onclick="copyDeepLink('${esc(post.x_post_id)}', '${shareId}')"
```

If `post.x_post_id` or `shareId` ever contains a literal single quote, the generated
HTML attribute is syntactically broken (the single quote terminates the JS string
literal prematurely). The same pattern appears in `shareId` which is derived from
`share-${esc(post.x_post_id)}` — same exposure.

X post IDs are currently numeric strings (`"1234567890"`), so the practical risk is
near-zero today. But the `esc()` helper is documented as the XSS defense for all user
content, and its omission of `'` is an undocumented gap that will silently break if
post ID format ever changes.

**Fix (option A — fix `esc()`):**

```js
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
```

**Fix (option B — use data attributes instead of inline JS):**

Replace the inline onclick with a data attribute and a delegated event listener:

```js
function renderCardFooter(post) {
  const xUrl = `https://x.com/i/web/status/${esc(post.x_post_id)}`;
  return `<div class="card-footer">
    <button class="share-btn" data-post-id="${esc(post.x_post_id)}"
      title="Copy link to this post">📤</button>
    <a href="${xUrl}" target="_blank" rel="noopener noreferrer" class="view-on-x">View on X</a>
  </div>`;
}
```

Then handle it with a delegated listener on `#post-list`. This is the more robust
pattern but requires more refactoring. Option A is the minimal fix.

---

## Info

### IN-01: `copyDeepLink()` clipboard failure is silently swallowed with no user feedback

**File:** `src/services/static_export.py:884-886` (generated `copyDeepLink` JS)

**Issue:** The `.catch()` handler in `copyDeepLink()` is empty — a comment says
"silent fail" for non-HTTPS. This is acceptable for HTTPS deployments (Netlify),
but when the clipboard write fails the user gets no visual feedback. The button
stays as `📤` with no indication the copy was skipped. Users on HTTP or with
restrictive permissions will silently get nothing.

```js
}).catch(function() {
  // clipboard denied in non-HTTPS context — silent fail
});
```

**Fix:** Provide a minimal text fallback in the catch:

```js
}).catch(function() {
  const btn = document.getElementById(btnId);
  if (btn) { btn.textContent = 'Copy failed'; setTimeout(function() { btn.innerHTML = '📤'; }, 1500); }
});
```

This is low severity given Netlify HTTPS is the target deployment, but a small
improvement to user experience.

---

### IN-02: No test verifying `#xbm-home-btn` is hidden by default (non-deep-link)

**File:** `tests/test_static_export_service.py:354-443` (`TestIndexHtmlDeepLink`)

**Issue:** `TestIndexHtmlDeepLink` tests that the features exist (string presence),
but there is no test that verifies the XBM Home button is visually hidden outside
deep-link mode. The CSS bug described in WR-01 would not be caught by any current
test. A regression test that asserts `#xbm-home-btn { display: none; }` is present
as a global (non-media-query) rule in the generated HTML would catch a recurrence.

**Fix:** Add a test to `TestIndexHtmlDeepLink`:

```python
def test_xbm_home_btn_hidden_by_default_globally(self, temp_db_v6, tmp_path):
    """DL-08b: #xbm-home-btn has a global display:none outside media query."""
    from src.services.static_export import StaticExportService
    svc = StaticExportService(temp_db_v6)
    svc.export(tmp_path)
    html = (tmp_path / "index.html").read_text()
    # The rule must appear before any @media block to be a global default.
    # A simple proxy: '#xbm-home-btn { display: none' must appear in the stylesheet
    # without being preceded only by @media on the same line.
    assert "#xbm-home-btn { display: none" in html
```

This is a static string check — it does not guarantee correct media-query scoping,
but it catches the absence of the global hide rule entirely.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
