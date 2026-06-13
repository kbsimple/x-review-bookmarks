---
plan: 14-03
phase: 14
wave: 3
status: complete
completed_at: 2026-06-13
duration_minutes: 5
tasks_completed: 2
files_created: 0
files_modified: 2
commit: 75e3919
subsystem: static-export
tags: [static-export, html, netlify, viewer, xss-mitigation]
requires: [14-02]
provides: [index.html-generation, netlify.toml-generation]
affects: [StaticExportService, export-result]
tech_stack_added: []
tech_stack_patterns: [single-file-html, inline-css-js, vanilla-js-fetch]
key_files_created: []
key_files_modified:
  - src/services/static_export.py
  - tests/test_static_export_service.py
key_decisions:
  - HTML generated as single Python string constant via _build_index_html() -- no templating library needed
  - All user content escaped via esc() before innerHTML insertion (XSS mitigation T-14-03-01)
  - Footer uses Unicode middle dot character for separator to avoid encoding issues in Python string
---

# Phase 14 Plan 03: index.html + netlify.toml Generation Summary

Single-file static viewer (dark theme, vanilla JS fetch + filter/sort) and Netlify deployment config added to StaticExportService.

## What Was Done

- Added `_NETLIFY_TOML` class-level constant with `[build]` section and `Cache-Control: public, max-age=0, must-revalidate` headers for both `/*.json` and `/index.html`
- Added `_write_netlify_toml(output_dir)` method — writes the constant to `netlify.toml`
- Added `_write_index_html(output_dir)` and `_build_index_html()` — generates a single self-contained HTML viewer with inline CSS (dark theme, UI-SPEC design tokens) and vanilla JS
- JS bootstrap: `Promise.all` fetches all 5 JSON files, populates `allPosts`, `searchIndex`, `reviewMap`
- Client-side filter+sort: text search via `Array.filter`, date ranges via `getDateRange()`, sort by newest/oldest/author
- Card renderers: `renderOriginalCard`, `renderRetweetCard`, `renderQuoteCard` with embedded card support
- `esc()` helper escapes all user content before `innerHTML` insertion (XSS prevention)
- Wired both into `export()` — `result.files` now contains 7 paths (5 JSON + `index.html` + `netlify.toml`)
- Activated `TestIndexHtml` (6 tests) and `TestNetlifyToml` (3 tests) — all pass
- `test_static_export_service.py`: 27 passed, 0 skipped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Merged main into worktree before execution**
- **Found during:** Task 1 start
- **Issue:** Worktree branch (`worktree-agent-ac5cd50fe4d0f13a9`) was created from `main` at `f32625e`, before the 14-02 merge (`ef79e4b`) landed. `src/services/static_export.py` did not exist in the worktree.
- **Fix:** `git merge main --no-edit` fast-forwarded the worktree branch to include all Wave 2 work
- **Commit:** merge was local (no separate commit created — fast-forward merge)

**2. [Rule 1 - Bug] Plan's verification script had incomplete schema**
- **Found during:** Task 1 verification
- **Issue:** The plan's inline verification script created `tags` and `topics` tables without `created_at` columns, which `list_tags()` and `list_topics()` query. This caused `sqlite3.OperationalError`.
- **Fix:** Added `created_at TEXT` to both table definitions in the ad-hoc verification script. The actual code and test fixture (`temp_db_v6`) are correct — this was only the plan's quickcheck script.
- **Impact:** None to production code; verification now passes cleanly.

## Known Stubs

None. All generated content is wired to real data fetched from the 5 JSON files at runtime.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: xss | src/services/static_export.py | index.html renders user bookmark data via innerHTML; mitigated by esc() helper covering all user-sourced fields |

## Self-Check: PASSED

- `src/services/static_export.py` exists and contains `_build_index_html`, `_write_index_html`, `_write_netlify_toml`, `_NETLIFY_TOML`
- `tests/test_static_export_service.py` has no `@pytest.mark.skip` in TestIndexHtml or TestNetlifyToml
- Commit `75e3919` exists in git log
- 27 tests pass, 0 skipped in `test_static_export_service.py`
- Full suite: 602 passed, 6 pre-existing failures in `test_cli_lan_cert.py`, 4 Wave-4 skips
