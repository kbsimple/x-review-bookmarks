---
phase: 16-viewer-presentation-modes
plan: "00"
subsystem: testing
tags: [pytest, tdd, static-export, carousel, viewer]

# Dependency graph
requires:
  - phase: 15-oembed-rich-embeds
    provides: StaticExportService with _build_index_html() and twttr.widgets.load already present
provides:
  - TestIndexHtmlCarousel class with 6 failing test stubs for carousel mode assertions
affects: [16-01-viewer-presentation-modes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 TDD stub class appended to existing test file — insert between last class and next class"

key-files:
  created: []
  modified:
    - tests/test_static_export_service.py

key-decisions:
  - "test_oembed_reinit_called_in_carousel PASSES in RED because twttr.widgets.load already present from Phase 15 — this is expected and acceptable"

patterns-established:
  - "Wave 0 RED stubs: class appended after existing test class, before next class, with blank line separators"

requirements-completed:
  - VIEWER-01
  - VIEWER-02
  - VIEWER-03
  - VIEWER-04
  - VIEWER-05

# Metrics
duration: 5min
completed: 2026-06-13
---

# Phase 16 Plan 00: Viewer Presentation Modes Summary

**TestIndexHtmlCarousel class with 6 pytest stubs asserting carousel mode strings absent from index.html — Wave 0 RED gate for VIEWER-01 through VIEWER-05**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-13T22:00:00Z
- **Completed:** 2026-06-13T22:02:27Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Appended `TestIndexHtmlCarousel` class to `tests/test_static_export_service.py` between `TestIndexHtml` and `TestNetlifyToml`
- 6 test methods covering carousel mode assertions (VIEWER-01 through VIEWER-05)
- 5/6 stubs fail correctly (RED phase); 1 passes because `twttr.widgets.load` was already present from Phase 15
- Zero regressions in existing `TestIndexHtml` (8 tests still pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TestIndexHtmlCarousel stub class with 6 failing assertions** - `21b7580` (test)

## Files Created/Modified
- `tests/test_static_export_service.py` - Added TestIndexHtmlCarousel class with 6 carousel test stubs (58 insertions)

## Decisions Made
- `test_oembed_reinit_called_in_carousel` passes even in RED because `twttr.widgets.load` is already in index.html from Phase 15's oEmbed stream path. The plan explicitly anticipated this — 5 of 6 stubs fail, which satisfies the Wave 0 exit criterion.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 RED stubs are in place and committed
- Wave 1 (plan 16-01) can now implement carousel mode in `_build_index_html()` to make all 6 stubs green
- No blockers

## TDD Gate Compliance

- RED gate commit present: `21b7580` (test(16-00): add failing TestIndexHtmlCarousel stubs)
- GREEN gate: deferred to Wave 1 (plan 16-01) per plan design — this is Wave 0 only

## Self-Check: PASSED

- `tests/test_static_export_service.py` — FOUND
- Commit `21b7580` — FOUND

---
*Phase: 16-viewer-presentation-modes*
*Completed: 2026-06-13*
