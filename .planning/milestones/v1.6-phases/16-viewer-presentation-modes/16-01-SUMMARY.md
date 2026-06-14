---
phase: 16-viewer-presentation-modes
plan: "01"
subsystem: ui
tags: [javascript, html, css, carousel, stream, localstorage, keyboard-nav, oembed]

# Dependency graph
requires:
  - phase: 16-viewer-presentation-modes
    provides: Wave 0 test stubs (TestIndexHtmlCarousel — 6 failing tests as RED gates)
provides:
  - Stream/Carousel mode switcher pill in viewer header
  - setMode() function: localStorage persistence, scroll save/restore, body class toggle
  - renderCarousel() function: single-post view with prev/next nav, keyboard nav, oEmbed support
  - Modified renderView(): carousel branch with carouselIndex reset
  - Global keydown listener: ArrowRight/ArrowLeft navigation, Escape to stream
affects:
  - 16-02 (any future wave adding modes or viewer features)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Carousel-as-mode: viewer toggled via body class + JS currentMode global rather than separate page"
    - "Mode persistence: localStorage key xbm_mode read at page load, written in setMode()"
    - "Carousel scroll: window.scrollTo(0,0) after each render, savedScrollY restored on return to stream"
    - "Anti-pattern avoided: filterAndSort() called in renderView, results passed as parameter to renderCarousel"

key-files:
  created: []
  modified:
    - src/services/static_export.py

key-decisions:
  - "Carousel index always resets to 0 on filter/sort/search change (simpler UX, avoids out-of-bounds)"
  - "Keyboard listener added once at page load outside renderView() to avoid duplicate registration"
  - "twttr.widgets.load scoped to post-list element, not document, to avoid re-processing entire DOM"
  - "localStorage value 'invalid' falls back safely: currentMode !== 'carousel' guard catches it"

patterns-established:
  - "Mode branching in renderView(): check currentMode early, delegate to mode-specific renderer, return early"
  - "renderCarousel() receives results[] as parameter (never calls filterAndSort() internally)"

requirements-completed:
  - VIEWER-01
  - VIEWER-02
  - VIEWER-03
  - VIEWER-04
  - VIEWER-05
  - VIEWER-06

# Metrics
duration: 8min
completed: 2026-06-13
---

# Phase 16 Plan 01: Viewer Presentation Modes Summary

**Stream/Carousel mode switcher with localStorage persistence, keyboard navigation, and oEmbed support — 6 new tests green, 628 total passing**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-13T05:47:12Z
- **Completed:** 2026-06-13T05:55:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added Stream/Carousel pill switcher in viewer header with active state styling
- Implemented `setMode()` with scroll save/restore, localStorage write, body class toggle
- Implemented `renderCarousel()` with single-post display, prev/next nav buttons, click handlers, oEmbed widget reload
- Modified `renderView()` to branch on `currentMode` with `carouselIndex` reset
- Added global `keydown` listener for ArrowRight/ArrowLeft/Escape keyboard navigation
- All 6 `TestIndexHtmlCarousel` stubs now green; full suite 628/628 passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CSS, HTML mode switcher, and JS globals** - `aab6752` (feat)
2. **Task 2: Add setMode(), renderCarousel(), keyboard nav; modify renderView()** - `78a933b` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `src/services/static_export.py` - Extended `_build_index_html()` with ~108 new lines across 6 insertion points: CSS rules, HTML mode switcher buttons, JS globals, setMode(), renderCarousel(), modified renderView(), and keydown listener

## Decisions Made

- Carousel index resets to 0 on every `renderView()` call in carousel mode — simpler UX, no out-of-bounds risk
- Keyboard listener registered once outside `renderView()` to avoid duplicate event registration
- `twttr.widgets.load` scoped to `document.getElementById('post-list')` not `document` per anti-pattern guidance in RESEARCH.md
- `filterAndSort()` called only in `renderView()` and keyboard listener; `renderCarousel()` receives results as parameter

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all three edits per task applied cleanly on first attempt. Test suite green after each task.

## Known Stubs

None - carousel renders real post data via existing `renderPost()` / `allPosts` / `reviewMap` globals. Counter uses numeric `idx + 1 / total`. No placeholder content.

## Threat Flags

None - carousel path calls `renderPost()` which uses `esc()` for all user-controlled strings. Counter values are numeric. localStorage value is compared to string literals only, never injected into DOM.

## Self-Check

- [x] `src/services/static_export.py` modified
- [x] `aab6752` commit exists
- [x] `78a933b` commit exists
- [x] 628 tests pass

## Next Phase Readiness

- Wave 1 complete — Stream/Carousel feature fully implemented and tested
- Wave 2 (if planned) could add additional modes (e.g., Focus/Reading mode) using same mode-branching pattern established here
- Netlify deployment of updated viewer ready for manual verification at https://xbm-viewer-export.netlify.app

---
*Phase: 16-viewer-presentation-modes*
*Completed: 2026-06-13*
