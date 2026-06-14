---
plan: 14-00
wave: 0
status: complete
completed_at: 2026-06-13
phase: "14"
subsystem: test-infrastructure
tags: [testing, fixtures, static-export, stubs]
dependency_graph:
  requires: [temp_db_v5]
  provides: [temp_db_v6, test_static_export_service stubs, test_export_static_cli stubs]
  affects: [tests/conftest.py]
tech_stack:
  added: []
  patterns: [fixture-chaining, pytest-skip-stubs]
key_files:
  modified: [tests/conftest.py]
  created:
    - tests/test_static_export_service.py
    - tests/test_export_static_cli.py
decisions:
  - "temp_db_v6 extends temp_db_v5 via fixture chaining (not a standalone fixture)"
  - "Seed 3 posts covering all post_type values (original, retweet, quote) for complete export coverage"
  - "stub tests use @pytest.mark.skip with wave reason strings for traceability"
metrics:
  duration: "~3 minutes"
  completed_at: "2026-06-13T18:14:02Z"
  task_count: 2
  file_count: 3
---

# Phase 14 Plan 00 Summary: Test Infrastructure

**One-liner:** Pytest fixture `temp_db_v6` with embedded_posts + 29 skipped stubs for static export tests.

## What Was Done

- Added `temp_db_v6` fixture to `tests/conftest.py` extending `temp_db_v5` with:
  - `embedded_posts` table (mirrors posts structure per SCHEMA_V6_MIGRATION)
  - `post_type` and `embedded_post_id` columns on `posts` via `ALTER TABLE` (with `OperationalError` guard for idempotency)
  - Seed data: 2 embedded posts (emb_001 for retweet, emb_002 for quote), 3 posts (original/retweet/quote), 2 tags (python/ml), 2 topics (Programming/Machine Learning), 2 review states (post_001 and post_002)
- Created `tests/test_static_export_service.py` with 4 test classes:
  - `TestStaticExportService` — 12 stubs (Wave 1 fills)
  - `TestSearchIndex` — 4 stubs (Wave 1 fills)
  - `TestIndexHtml` — 6 stubs (Wave 3 fills)
  - `TestNetlifyToml` — 3 stubs (Wave 3 fills)
- Created `tests/test_export_static_cli.py` with `TestExportStaticCLI` — 4 stubs (Wave 4 fills)
- All 29 stubs collected by pytest and skipped (0 failures)

## Verification

- `pytest tests/test_static_export_service.py tests/test_export_static_cli.py --collect-only`: 29 items collected
- `pytest tests/test_static_export_service.py tests/test_export_static_cli.py -q`: 29 skipped, 0 failed
- Full suite: 575 passed, 29 skipped, 6 pre-existing failures in test_cli_lan_cert.py (not introduced by this plan)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

All 29 tests are intentional stubs. They are tracked for Wave 1, Wave 3, and Wave 4 executors to fill in. None prevent this plan's goal (test scaffold) from being achieved.

## Self-Check: PASSED

- `tests/conftest.py` modified: FOUND
- `tests/test_static_export_service.py`: FOUND
- `tests/test_export_static_cli.py`: FOUND
- Commit `54b9731`: FOUND
