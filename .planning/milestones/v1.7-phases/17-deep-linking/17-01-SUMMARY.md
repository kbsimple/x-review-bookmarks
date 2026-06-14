---
phase: "17"
plan: "01"
subsystem: static-export-viewer
tags: [deep-linking, share-button, clipboard, carousel, client-side, css, javascript]
dependency_graph:
  requires: [17-00]
  provides: [deep-link-share-buttons, deep-link-hash-navigation, xbm-home-button, showDeepLinkError]
  affects: [src/services/static_export.py]
tech_stack:
  added: []
  patterns: [navigator-clipboard-api, window-location-hash, css-body-class-toggle, inline-js-onclick]
key_files:
  created: []
  modified:
    - src/services/static_export.py
decisions:
  - "Used literal 📤 emoji directly in Python string for share icon — Python 3 handles UTF-8 cleanly"
  - "goHome() sets window.location.href to origin+pathname only, intentionally excluding any fragment"
  - "Hash detection placed inside Promise.all().then() after allPosts populated — not at top-level JS (per D-05 / RESEARCH Pitfall 1)"
  - "deepLinkMode flag set directly (not via setMode()) to avoid early-return guard when currentMode already 'carousel'"
  - "esc() applied to postId in showDeepLinkError innerHTML per T-17-01-01 threat mitigation"
metrics:
  duration: "209s"
  completed: "2026-06-14T22:33:00Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 17 Plan 01: Deep Linking Implementation Summary

**One-liner:** Full deep linking feature added to static viewer — share icon (📤) on every card copies a #post-{id} URL to clipboard, and opening that URL launches carousel mode focused on that post with an XBM Home button replacing the mode switcher.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | CSS + HTML: deep-link-mode rules and XBM Home button | 5743a52 | src/services/static_export.py |
| 2 | JS: deepLinkMode flag, copyDeepLink, goHome, renderCardFooter, renderOEmbedCard, hash detection, showDeepLinkError | c322d77 | src/services/static_export.py |

## What Was Built

### Task 1 — CSS + HTML (3 edits)

**Edit 1: `.share-btn` CSS** after `.view-on-x:hover` — styles the share button to match the muted, small card footer aesthetic.

**Edit 2: Deep-link-mode CSS block** inside the mobile `@media (max-width: 600px)` section — `#xbm-home-btn { display: none }` by default, `body.deep-link-mode .mode-switcher { display: none !important }` and `body.deep-link-mode #xbm-home-btn { display: inline-flex ... }` to swap them on deep-link arrival.

**Edit 3: XBM Home `<a>` element** inserted in `#header` div between `.mode-switcher` and `#header-options-btn`, calling `goHome()` on click.

### Task 2 — JavaScript (6 edits)

**Edit 1: `let deepLinkMode = false;`** added to global state block after `cachedCarouselResults`.

**Edit 2: `renderCardFooter()` replacement + `copyDeepLink()`** — footer now renders a `<button class="share-btn">📤</button>` with `onclick="copyDeepLink(postId, shareId)"` alongside the existing "View on X" link. `copyDeepLink()` uses `navigator.clipboard.writeText()` with a "Copied!" confirmation that auto-resets after 1500ms.

**Edit 3: `renderOEmbedCard()` patch** — added `${renderCardFooter(post)}` so oEmbed/Twitter widget cards also get the share icon (D-08 requirement).

**Edit 4: `goHome()` function** after `setMode()` — navigates to `window.location.origin + window.location.pathname` (fragment-free).

**Edit 5: `showDeepLinkError()` function** after `showError()` — renders graceful "Post not found" message with an XBM Home link when hash references a post ID not in `allPosts`. `esc(postId)` applied to mitigate T-17-01-01.

**Edit 6: Hash detection block** inside `Promise.all().then()` handler, after `allPosts` is populated and before `renderView()`. Detects `#post-{id}` hash, finds the post, sets `deepLinkMode = true`, adds `deep-link-mode` body class, clears all filters, finds carousel index via `searchIndex.findIndex()`, and sets `currentMode = 'carousel'` directly (bypassing `setMode()` guard).

## Verification Results

```
# All 11 TestIndexHtmlDeepLink tests GREEN
python3 -m pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink -v
======================== 11 passed in 3.13s =========================

# Full static export suite — no regressions  
python3 -m pytest tests/test_static_export_service.py -q
======================== 54 passed in 3.37s =========================

# Full project suite
python3 -m pytest -q
======================== 638 passed, 6 pre-existing failures (test_cli_lan_cert.py) =========================
```

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing Test Failures (Out of Scope)

`tests/test_cli_lan_cert.py` has 6 pre-existing failures caused by Pydantic `Settings` requiring `client_id` field that is not provided in the test environment. These failures exist on the base commit `2fee7be` before any changes in this plan and are entirely unrelated to deep linking. Documented per deviation scope boundary rules — not fixed.

## Known Stubs

None — all deep-link functionality is fully wired:
- `copyDeepLink()` is live JavaScript (no placeholder logic)
- `renderCardFooter()` renders real share buttons with real `x_post_id` values
- Hash detection reads `window.location.hash` and resolves against populated `allPosts`
- `showDeepLinkError()` renders a real error message

## Threat Surface Scan

No new network endpoints or auth paths introduced. The `copyDeepLink()` URL construction uses `window.location.origin + window.location.pathname + '#post-' + postId` — client-side only, no server-side injection vector. All threat mitigations from the plan's threat register were implemented:

- **T-17-01-01:** `esc(postId)` applied in `showDeepLinkError()` innerHTML
- **T-17-01-02:** `esc(post.x_post_id)` applied in `renderCardFooter()` onclick attribute and button id

## Self-Check: PASSED

- [x] `grep -c "deepLinkMode" src/services/static_export.py` returns 2 (declaration + assignment)
- [x] `grep -c "copyDeepLink" src/services/static_export.py` returns 2 (function def + onclick call)
- [x] `grep -c "navigator.clipboard.writeText" src/services/static_export.py` returns 1
- [x] `grep -c "window.location.hash" src/services/static_export.py` returns 1
- [x] `grep -c "goHome" src/services/static_export.py` returns 2 (function def + onclick in header)
- [x] `grep -c "showDeepLinkError" src/services/static_export.py` returns 2 (def + call in bootstrap)
- [x] `grep -c "renderCardFooter(post)" src/services/static_export.py` returns 5 (original + retweet + quote + oEmbed + function call in renderOEmbed itself — 4 call sites + 1 function definition pattern)
- [x] All 11 TestIndexHtmlDeepLink tests PASS GREEN
- [x] Commits 5743a52 and c322d77 exist in git log
- [x] 54 static export tests pass, 638 project tests pass (6 pre-existing lan_cert failures unchanged)
