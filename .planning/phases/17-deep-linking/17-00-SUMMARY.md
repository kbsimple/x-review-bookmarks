---
phase: "17"
plan: "00"
subsystem: test-infrastructure
tags: [tdd, red-stubs, deep-linking, static-export]
dependency_graph:
  requires: []
  provides: [TestIndexHtmlDeepLink-class, DL-01-through-DL-11-test-gates]
  affects: [tests/test_static_export_service.py]
tech_stack:
  added: []
  patterns: [string-grep-test-pattern, local-import-in-test-method]
key_files:
  created: []
  modified:
    - tests/test_static_export_service.py
decisions:
  - "All 11 DL tests use the identical 5-line pattern from TestIndexHtmlCarousel: local import, instantiate service, export, read index.html, assert string presence"
  - "TestIndexHtmlDeepLink placed between TestIndexHtmlCarousel (ends line 352) and TestNetlifyToml (pushed to line 446)"
metrics:
  duration: "80s"
  completed: "2026-06-14T22:06:32Z"
  tasks_completed: 1
  files_modified: 1
---

# Phase 17 Plan 00: Deep Linking RED Test Stubs Summary

**One-liner:** 11 RED failing stubs in TestIndexHtmlDeepLink establishing test gates for Phase 17 deep-linking feature (DL-01 through DL-11).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add TestIndexHtmlDeepLink class with 11 RED stubs | f524faa | tests/test_static_export_service.py |

## What Was Built

Inserted `TestIndexHtmlDeepLink` class into `tests/test_static_export_service.py` between `TestIndexHtmlCarousel` and `TestNetlifyToml`. The class contains 11 test methods covering every deep-linking requirement (DL-01 through DL-11):

- `test_share_btn_present` — DL-01: `share-btn` element
- `test_copy_deep_link_function_present` — DL-02: `copyDeepLink` function
- `test_clipboard_write_present` — DL-03: `navigator.clipboard.writeText`
- `test_hash_detection_present` — DL-04: `window.location.hash`
- `test_post_hash_prefix_present` — DL-05: `#post-` prefix string
- `test_deep_link_mode_flag_present` — DL-06: `deepLinkMode` flag
- `test_deep_link_mode_css_class_present` — DL-07: `deep-link-mode` CSS class
- `test_xbm_home_btn_present` — DL-08: `xbm-home-btn` element
- `test_go_home_function_present` — DL-09: `goHome` function
- `test_show_deep_link_error_present` — DL-10: `showDeepLinkError` function
- `test_xbm_home_text_present` — DL-11: `XBM Home` text

## Verification Results

```
tests/test_static_export_service.py::TestIndexHtmlDeepLink
FAILED (11 tests) — all RED as required

Full suite: 11 failed, 43 passed — no regressions
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — this plan intentionally creates failing tests (RED stubs). The stubs are not code stubs but test gates. They will be satisfied by Wave 1 implementation (Plan 17-01).

## Threat Flags

None — test-only change, no new network endpoints, auth paths, or production code.

## Self-Check: PASSED

- [x] `class TestIndexHtmlDeepLink` exists in tests/test_static_export_service.py (line 354)
- [x] 11 test methods present (test count went from 43 to 54)
- [x] All 11 tests FAIL RED (verified by pytest output)
- [x] 43 pre-existing tests still pass (no regressions)
- [x] `TestNetlifyToml` still exists (line 446)
- [x] Commit f524faa exists in git log
