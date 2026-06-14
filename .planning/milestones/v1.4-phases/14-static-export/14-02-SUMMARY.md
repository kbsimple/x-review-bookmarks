---
phase: "14"
plan: "02"
wave: 2
subsystem: static-export
status: complete
completed_at: 2026-06-13
duration_seconds: 372
tags:
  - static-export
  - json-writers
  - search-index
  - netlify
dependency_graph:
  requires:
    - "14-01: PostsRepository.get_all_with_embedded, ReviewStateRepository.get_all"
  provides:
    - "StaticExportService.export() -- 5 JSON file writers"
    - "StaticExportResult dataclass"
  affects:
    - "src/services/__init__.py -- new exports"
tech_stack:
  added: []
  patterns:
    - "Bulk JOIN queries for tag/topic maps (no N+1)"
    - "Sorted space-joined strings for denormalized search-index fields"
key_files:
  created:
    - src/services/static_export.py
    - tests/test_static_export_service.py
  modified:
    - src/services/__init__.py
    - src/repositories/posts.py
    - src/repositories/review_state.py
    - tests/conftest.py
decisions:
  - "StaticExportService is standalone (does not extend ExportService)"
  - "source field = 'xbm-static' distinguishes from CLI export ('xbm')"
  - "tags/topics strings in search-index are sorted alphabetically for deterministic output"
  - "Worktree synced Plan 14-01 additions (get_all_with_embedded, get_all, temp_db_v6)"
metrics:
  duration: "372 seconds"
  completed_date: "2026-06-13"
  tasks_completed: 2
  files_changed: 6
---

# Phase 14 Plan 02: StaticExportService + JSON Writers Summary

## One-liner

StaticExportService with 5 bulk-query JSON writers (posts, tags, topics, review_state, search-index) and 16 activated tests (12 service + 4 search-index).

## What Was Done

- Created `src/services/static_export.py` with `StaticExportService` class and `StaticExportResult` dataclass
- Implemented 5 JSON writers:
  - `_write_posts_json` -- all posts with inline tags, topics, embedded_post
  - `_write_tags_json` -- all tags with post_ids lists
  - `_write_topics_json` -- all topics with post_ids and hierarchy fields
  - `_write_review_state_json` -- all review states (no internal FSRS fields)
  - `_write_search_index_json` -- denormalized entries for client-side Array.filter()
- Bulk JOIN queries in `_build_post_tag_map()` and `_build_post_topic_map()` prevent N+1 queries
- posts.json embeds tags (list[str]), topics (list[{id, name}]), and embedded_post inline per post
- search-index.json entries have `created_at_ts` (int Unix timestamp), `tags` and `topics` as sorted space-joined strings for deterministic output
- Added `StaticExportService`, `StaticExportResult` exports to `src/services/__init__.py`
- Activated 12 `TestStaticExportService` + 4 `TestSearchIndex` tests -- all pass
- TestIndexHtml (6 tests) and TestNetlifyToml (3 tests) remain `@pytest.mark.skip` for Wave 3
- Module-level repository tests from Wave 1 preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree missing Plan 14-01 repository additions**
- **Found during:** Task 2 verification (fixture `temp_db_v6` not found)
- **Issue:** The worktree (agent-a4f96b9b05d541216) was created before Plan 14-01 executed on main. It lacked: `PostsRepository.get_all_with_embedded()`, `PostsRepository._row_to_dict_with_embedded()`, `ReviewStateRepository.get_all()`, and the `temp_db_v6` fixture in `tests/conftest.py`.
- **Fix:** Synced all four additions from the main project files into the worktree files. Methods are identical to what Plan 14-01 committed.
- **Files modified:** `src/repositories/posts.py`, `src/repositories/review_state.py`, `tests/conftest.py`
- **Commit:** 5def81c (included in main task commit)

## Test Results

| Class | Tests | Result |
|-------|-------|--------|
| TestStaticExportService | 12 | PASS |
| TestSearchIndex | 4 | PASS |
| TestIndexHtml | 6 | SKIP (Wave 3) |
| TestNetlifyToml | 3 | SKIP (Wave 3) |
| Module-level repo tests | 2 | PASS |
| **Total** | **27** | **18 pass, 9 skip** |

Full suite: 593 pass, 9 skip, 6 pre-existing failures in test_cli_lan_cert.py (known, out of scope).

## Self-Check: PASSED

- `src/services/static_export.py` -- FOUND
- `tests/test_static_export_service.py` -- FOUND
- Commit 5def81c -- FOUND
- 18 tests pass, 9 skip as expected
