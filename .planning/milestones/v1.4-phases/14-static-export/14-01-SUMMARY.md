---
plan: 14-01
phase: 14
wave: 1
status: complete
completed_at: 2026-06-13T18:21:11Z
subsystem: repositories
tags: [static-export, repositories, sqlite, export]
dependency_graph:
  requires: [14-00]
  provides: [PostsRepository.get_all_with_embedded, ReviewStateRepository.get_all]
  affects: [14-02]
tech_stack:
  added: []
  patterns: [LEFT JOIN with embedded_posts, column allowlisting for export fields]
key_files:
  created: []
  modified:
    - src/repositories/posts.py
    - src/repositories/review_state.py
    - tests/test_static_export_service.py
decisions:
  - get_all_with_embedded reuses existing _row_to_dict_with_embedded for JSON parsing consistency
  - get_all explicitly excludes user_preference, step, fsrs_data (internal FSRS fields not useful to viewer)
metrics:
  duration: ~7 minutes
  completed: 2026-06-13
  tasks_completed: 2
  files_modified: 3
---

# Phase 14 Plan 01: Repository Extensions Summary

**One-liner:** Added unbounded LEFT JOIN export method to PostsRepository and FSRS-field-stripped get_all to ReviewStateRepository.

## What Was Done

- Added `PostsRepository.get_all_with_embedded()` to `src/repositories/posts.py` — unbounded LEFT JOIN on embedded_posts, returns all posts ordered by created_at DESC with embedded_post key populated
- Added `ReviewStateRepository.get_all()` to `src/repositories/review_state.py` — returns post_id/scheduled_for/last_reviewed/review_count/stability/difficulty/state for all rows, ordered by post_id
- Activated `test_posts_json_retweet_has_embedded_post` and `test_posts_json_original_has_null_embedded_post` in `TestStaticExportService` class (removed @pytest.mark.skip decorators, added implementation using the new repository method)
- Added two standalone module-level tests: `test_get_all_with_embedded_returns_all_posts` and `test_get_all_review_states_returns_seeded_states`
- All 4 new/activated tests pass; full suite result: 583 passed, 27 skipped (same 6 pre-existing failures in test_cli_lan_cert.py unrelated to this plan)

## Key Decisions

- `get_all_with_embedded()` reuses existing `_row_to_dict_with_embedded()` helper for JSON parsing consistency — avoids duplicating media_urls/link_urls parsing logic
- `get_all()` explicitly names columns in SELECT (excludes user_preference, step, fsrs_data) since these are internal FSRS plumbing not needed by static viewer consumers
- Method inserted after `get_all_ordered()` and before `count()` to keep unbounded-export methods grouped together

## Deviations from Plan

### Pre-existing Setup Required

**[Rule 3 - Blocking Issue] Worktree was behind main by plan 14-00 changes**
- **Found during:** Initial setup before Task 1
- **Issue:** The worktree branch did not have the `temp_db_v6` fixture or `test_static_export_service.py` from plan 14-00, which was committed in another agent worktree and then merged to main
- **Fix:** Merged main into the worktree branch (`git merge main --no-edit`) — fast-forward merge with no conflicts
- **Files affected:** `.planning/` artifacts, `tests/conftest.py`, `tests/test_static_export_service.py`, `tests/test_export_static_cli.py`
- **Commit:** 1e8897a (merge commit already on main, applied to worktree)

None for the actual plan tasks — implementation executed exactly as written.

## Known Stubs

None — both repository methods are fully implemented and tested.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Both new methods are read-only SELECT queries on existing tables.

## Self-Check: PASSED

- `src/repositories/posts.py` modified: FOUND (get_all_with_embedded method at line 220)
- `src/repositories/review_state.py` modified: FOUND (get_all method after get_stats)
- `tests/test_static_export_service.py` modified: FOUND (4 new/activated tests)
- Commit 999e797: FOUND
