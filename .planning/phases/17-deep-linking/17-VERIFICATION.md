---
phase: 17-deep-linking
verified: 2026-06-14T23:00:00Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open Netlify deploy, click share icon (📤) on a post card in both stream and carousel mode"
    expected: "Clipboard receives a URL of the form https://xbm-viewer-export.netlify.app/#post-{id}; button briefly shows 'Copied!' then reverts to 📤 icon after ~1500ms"
    why_human: "navigator.clipboard.writeText() requires HTTPS and a user gesture; untestable by string grep or python process"
  - test: "Navigate directly to https://xbm-viewer-export.netlify.app/#post-{valid_id} (pick a real post ID from the export)"
    expected: "Page loads in carousel mode, filters are cleared, the linked post is the first post shown, and the header shows 'XBM Home' button instead of the Carousel/Stream mode switcher"
    why_human: "Browser hash routing and DOM manipulation cannot be verified by static HTML string inspection"
  - test: "While on a deep-link URL, click 'XBM Home'"
    expected: "Navigates to https://xbm-viewer-export.netlify.app/ (no hash fragment), full viewer loads with user's persisted mode, no XBM Home button visible"
    why_human: "window.location.href navigation and page reload behavior are browser-runtime only"
  - test: "Navigate to https://xbm-viewer-export.netlify.app/#post-fake999 (an ID that does not exist)"
    expected: "Page shows 'Post not found' error with the post ID displayed and an 'XBM Home' link; no crash"
    why_human: "showDeepLinkError() DOM mutation and rendering of the error-state element requires a real browser"
---

# Phase 17: Deep Linking Verification Report

**Phase Goal:** Add shareable deep link URLs to the static viewer. A share icon (📤) on each post card copies a `#post-{id}` hash URL to the clipboard. Opening that URL opens the viewer in a focused carousel view (filters cleared, that post shown) with an "XBM Home" button in the header to return to the full viewer.

**Verified:** 2026-06-14T23:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Share icon (📤) appears on every post card in both stream and carousel mode | VERIFIED | `renderCardFooter(post)` called in `renderOriginalCard` (line 903), `renderRetweetCard` (914), `renderQuoteCard` (927), `renderOEmbedCard` (948). All 4 card renderers include the share button. |
| 2 | Clicking share icon copies a `#post-{x_post_id}` URL to clipboard with visual confirmation | VERIFIED (static) | `copyDeepLink()` function at line 876 calls `navigator.clipboard.writeText(url)` where `url = window.location.origin + window.location.pathname + '#post-' + postId`. Button shows 'Copied!' with 1500ms reset. Visual behavior requires human verification. |
| 3 | Opening a URL with `#post-{id}` hash opens viewer in carousel mode showing that post with all filters cleared | VERIFIED (static) | Hash detection at lines 1171–1189 inside Promise.all().then() handler, after allPosts populated (line 1164), before renderView() (line 1190). Sets deepLinkMode=true, adds deep-link-mode class, clears search-input/date-filter/sort-order, sets carousel mode. Actual navigation behavior requires human verification. |
| 4 | Header shows XBM Home button (replacing mode switcher) when arrived via deep link | VERIFIED | `#xbm-home-btn` HTML at line 663. CSS at lines 427–437 (global, not media-scoped): `#xbm-home-btn { display: none; }` globally, `body.deep-link-mode #xbm-home-btn { display: inline-flex ... }` when deep-link-mode active, `.mode-switcher` hidden via `body.deep-link-mode .mode-switcher { display: none !important; }`. |
| 5 | XBM Home navigates to root URL with no hash | VERIFIED | `goHome()` at line 973: `window.location.href = window.location.origin + window.location.pathname` — correct fragment-free URL construction. |
| 6 | If post ID is not found in allPosts, a graceful error is shown with XBM Home link | VERIFIED (static) | `showDeepLinkError(postId)` at line 1037 uses `esc(postId)` for XSS safety, renders "Post not found" with XBM Home link. Called at line 1186. Rendering behavior requires human verification. |
| 7 | Share icon appears on oEmbed (rich embed) cards | VERIFIED | `renderOEmbedCard` at line 943 includes `${renderCardFooter(post)}` at line 948 — confirmed via code read and grep count of `renderCardFooter(post)` call sites (4 card renderers). |

**Score:** 7/7 truths verified (structural/static); 4 truths have browser-runtime aspects requiring human verification

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/services/static_export.py` | Deep linking feature in `_build_index_html()` | VERIFIED | All 8 integration points present: CSS rules, XBM Home button HTML, deepLinkMode flag, copyDeepLink(), goHome(), renderCardFooter() replacement, renderOEmbedCard() patch, hash detection block, showDeepLinkError() |
| `tests/test_static_export_service.py` | `TestIndexHtmlDeepLink` class with 11 test methods | VERIFIED | Class at line 354, 11 test methods confirmed, TestNetlifyToml preserved at line 446 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `renderCardFooter()` | `copyDeepLink(postId, btnId)` | onclick attribute on share button | WIRED | Line 870: `onclick="copyDeepLink('${esc(post.x_post_id)}', '${shareId}')"` |
| `renderOEmbedCard()` | `renderCardFooter(post)` | template literal inclusion | WIRED | Line 948: `${renderCardFooter(post)}` |
| Bootstrap `Promise.all().then()` | `allPosts[postId]` lookup | `window.location.hash` detection | WIRED | Lines 1171–1189: hash read after allPosts populated at line 1164, before renderView() at 1190 |
| `body.deep-link-mode` | `.mode-switcher` / `#xbm-home-btn` | CSS visibility rules | WIRED | Lines 426–437: global CSS (not media-scoped) hides switcher, shows home button |
| `#xbm-home-btn` | `goHome()` | onclick attribute | WIRED | Line 663: `onclick="goHome()"` |
| `showDeepLinkError()` | `#error-state` element | innerHTML write with `esc()` | WIRED | Line 1037–1044: writes to `document.getElementById('error-state')` using `esc(postId)` |

### Data-Flow Trace (Level 4)

Not applicable — this is a client-side static HTML generator. All data flows are inline JavaScript within the generated HTML; no server-side data rendering or React state involved. The Python code generates the HTML string; runtime behavior is client-side only.

### Behavioral Spot-Checks

Step 7b: SKIPPED — All behaviors require a running browser with HTTPS. The generated `index.html` is static and its JavaScript cannot be executed in a Python process context.

### Requirements Coverage

Note: No central `REQUIREMENTS.md` file exists in `.planning/`. Requirement IDs DL-01 through DL-11 are defined exclusively within the phase PLAN and VALIDATION files. No orphaned requirements found — all 11 IDs claimed in both PLANs are accounted for and verified below.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DL-01 | 17-00, 17-01 | share-btn element present in generated HTML | SATISFIED | `share-btn` CSS at line 558, button in `renderCardFooter` at line 869 |
| DL-02 | 17-00, 17-01 | `copyDeepLink` function present | SATISFIED | Function defined at line 876 |
| DL-03 | 17-00, 17-01 | `navigator.clipboard.writeText` call present | SATISFIED | Line 878: `navigator.clipboard.writeText(url)` |
| DL-04 | 17-00, 17-01 | `window.location.hash` read present | SATISFIED | Line 1171: `const hash = window.location.hash;` |
| DL-05 | 17-00, 17-01 | `#post-` prefix string present | SATISFIED | Line 1172: `hash.startsWith('#post-')` and line 877: `'#post-' + postId` |
| DL-06 | 17-00, 17-01 | `deepLinkMode` flag declared | SATISFIED | Line 752: `let deepLinkMode = false;` |
| DL-07 | 17-00, 17-01 | `deep-link-mode` CSS class present | SATISFIED | Lines 428–437: `body.deep-link-mode` CSS rules |
| DL-08 | 17-00, 17-01 | `xbm-home-btn` element present in header HTML | SATISFIED | Line 663: `<a ... id="xbm-home-btn" ... >XBM Home</a>` |
| DL-09 | 17-00, 17-01 | `goHome` function present | SATISFIED | Line 973: `function goHome()` |
| DL-10 | 17-00, 17-01 | `showDeepLinkError` function present | SATISFIED | Line 1037: `function showDeepLinkError(postId)` |
| DL-11 | 17-00, 17-01 | "XBM Home" text present in HTML | SATISFIED | Line 663 (header button) and line 1043 (error state link) |

All 11 DL requirements satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/services/static_export.py` | 1043 | `esc(window.location.origin + window.location.pathname)` | Info | The `window.location.origin + window.location.pathname` expression is a browser-controlled property (not user input), so `esc()` is technically redundant here, but applying it is the correct defensive convention and causes no harm. |

No blockers or warnings found. One informational note on defensive `esc()` usage that is correct-by-convention.

### Human Verification Required

#### 1. Share Icon Clipboard Copy

**Test:** Open the Netlify viewer at https://xbm-viewer-export.netlify.app, navigate to any post card in stream or carousel mode, click the 📤 share icon.
**Expected:** Button briefly shows "Copied!" text, reverts to 📤 after ~1500ms; paste the clipboard content and confirm it is a URL of the form `https://xbm-viewer-export.netlify.app/#post-{numeric_id}`.
**Why human:** `navigator.clipboard.writeText()` requires HTTPS and a user gesture; cannot be exercised by pytest or a Python subprocess.

#### 2. Deep Link Hash Navigation

**Test:** Open `https://xbm-viewer-export.netlify.app/#post-{valid_id}` in a browser (substitute a real post ID from a known bookmark).
**Expected:** Page loads directly into carousel mode, search/date/sort filters are empty/reset, the linked post is shown first, header displays the "XBM Home" button and the Carousel/Stream mode switcher is hidden.
**Why human:** `window.location.hash` detection, DOM manipulation, and carousel rendering require a real browser runtime.

#### 3. XBM Home Navigation

**Test:** After arriving via a deep link (step 2 above), click the "XBM Home" button in the header.
**Expected:** Browser navigates to `https://xbm-viewer-export.netlify.app/` (no `#` fragment), viewer reloads into full post list with the user's persisted mode, XBM Home button is no longer visible.
**Why human:** `window.location.href` navigation and page reload behavior require browser execution.

#### 4. Post Not Found Error

**Test:** Open `https://xbm-viewer-export.netlify.app/#post-fake999` (a post ID that does not exist in the export).
**Expected:** Page shows a "Post not found" error message with the bad ID displayed and a clickable "XBM Home" link. No JavaScript crash or blank page.
**Why human:** `showDeepLinkError()` DOM mutation requires a real browser; the post ID render path uses `esc()` but XSS safety can only be confirmed in a browser devtools inspection.

### Gaps Summary

No gaps found. All 7 observable truths are structurally verified, all 11 DL requirements are satisfied, all key links are wired, and the full test suite passes (644/644 tests). The 4 human verification items above are standard browser-runtime behaviors that cannot be tested by static code inspection — they do not indicate missing implementation, only the inherent limitation of string-grep testing for client-side JavaScript.

**Notable finding:** The SUMMARY.md for Wave 1 (17-01) incorrectly states the deep-link-mode CSS was placed inside the mobile `@media (max-width: 600px)` block. The actual implementation correctly places it globally before the media query (lines 426–437), with a comment explicitly noting "global — not media-scoped". This is a SUMMARY documentation error, not an implementation error — the code behavior is correct.

---

_Verified: 2026-06-14T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
