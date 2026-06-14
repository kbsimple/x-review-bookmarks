---
phase: 08-storage-foundation
plan: 00
subsystem: storage
tags: [tdd, tests, schema, repository, sync]
requires: []
provides: [test-scaffolding-for-v6-migration, test-scaffolding-for-embedded-posts-repo, test-scaffolding-for-sync-integration]
affects: []
tech_stack:
  added: []
  patterns: [pytest, TDD-RED-phase]
key_files:
  created:
    - tests/test_embedded_posts_repository.py
  modified:
    - tests/test_migrations.py
    - tests/test_sync_service.py
decisions:
  - TDD approach - create failing tests before implementation
  - Test structure follows existing patterns from tests/conftest.py
  - Fixtures use temp_db_v5 extended to temp_db_v6 with embedded_posts table
duration_seconds: 290
completed_at: "2026-06-04T09:05:38Z"
---

# Phase 08 Plan 00: Test Scaffolding for Storage Foundation Summary

## One-liner

Created failing test scaffolding for V6 schema migration, EmbeddedPostsRepository, and embedded post sync integration following TDD RED phase.

## What Was Done

### Task 1: Migration Test Scaffolding for Schema V6

Added `TestMigrateToV6` class to `tests/test_migrations.py` with 6 failing tests:

1. `test_migrate_to_v6_function_exists` - Verifies `migrate_to_v6` function exists in migrations module
2. `test_migrate_to_v6_creates_embedded_posts_table` - Verifies `embedded_posts` table created with correct columns (x_post_id, created_at, text, author_id, author_username, author_display_name, media_urls, link_urls, available)
3. `test_migrate_to_v6_adds_post_type_column` - Verifies `posts.post_type` column added with default 'original'
4. `test_migrate_to_v6_adds_embedded_post_id_column` - Verifies `posts.embedded_post_id` column added (nullable TEXT)
5. `test_migrate_to_v6_is_idempotent` - Verifies migration can be called multiple times safely
6. `test_get_schema_version_returns_v6` - Verifies `get_schema_version()` returns "v6" after migration

**Commit:** `5405438`

### Task 2: EmbeddedPostsRepository Test Scaffolding

Created `tests/test_embedded_posts_repository.py` with `TestEmbeddedPostsRepository` class containing 5 failing tests:

1. `test_upsert_embedded_post_inserts_new` - Verifies new embedded post insertion
2. `test_upsert_embedded_post_updates_existing` - Verifies upsert updates existing on conflict
3. `test_get_by_id_returns_dict` - Verifies retrieval returns dict with all fields
4. `test_get_by_id_returns_none_for_nonexistent` - Verifies None returned for unknown posts
5. `test_upsert_embedded_post_handles_unavailable` - Verifies unavailable flag handled correctly

**Commit:** `93e7d94`

### Task 3: Embedded Post Sync Integration Test Scaffolding

Added `TestEmbeddedPostsSync` class to `tests/test_sync_service.py` with 5 failing tests:

1. `test_store_tweet_sets_post_type_original` - Original posts have `post_type='original'`
2. `test_store_tweet_sets_post_type_retweet` - Retweets have `post_type='retweet'` with embedded_post_id
3. `test_store_tweet_sets_post_type_quote` - Quote tweets have `post_type='quote'` with embedded_post_id
4. `test_store_tweet_handles_unavailable_embedded` - Unavailable originals marked with `available=False`
5. `test_store_tweet_stores_embedded_post_content` - Embedded post content stored when available

**Commit:** `aff853d`

## Deviations from Plan

None - plan executed exactly as written. All tests fail as expected for TDD RED phase.

## Test Results

All 16 tests fail with expected errors:

| Test File | Tests | Failure Type |
|-----------|-------|--------------|
| test_migrations.py::TestMigrateToV6 | 6 | ImportError: cannot import name 'migrate_to_v6' |
| test_embedded_posts_repository.py | 5 | ModuleNotFoundError: No module named 'src.repositories.embedded_posts' |
| test_sync_service.py::TestEmbeddedPostsSync | 5 | AssertionError / ModuleNotFoundError |

## Files Modified

| File | Lines Added | Purpose |
|------|-------------|---------|
| tests/test_migrations.py | +127 | V6 migration test class |
| tests/test_embedded_posts_repository.py | +243 | New file for repository tests |
| tests/test_sync_service.py | +279 | Embedded posts sync test class |

## Requirements Coverage

| Requirement | Test Coverage |
|-------------|---------------|
| STR-01: Schema migration adds embedded_posts table | `test_migrate_to_v6_creates_embedded_posts_table` |
| STR-02: Posts table gains post_type, embedded_post_id columns | `test_migrate_to_v6_adds_post_type_column`, `test_migrate_to_v6_adds_embedded_post_id_column` |
| STR-03: Unavailable originals detection | `test_upsert_embedded_post_handles_unavailable`, `test_store_tweet_handles_unavailable_embedded` |

## Next Steps

Plan 01 will implement:
1. `SCHEMA_V6_MIGRATION` constant in `src/db/schema.py`
2. `migrate_to_v6()` function in `src/db/migrations.py`
3. Update `get_schema_version()` to return "v6"

Plan 02 will implement:
1. `src/repositories/embedded_posts.py` with `EmbeddedPostsRepository` class

Plan 03 will implement:
1. Update `SyncService._store_tweet()` to handle referenced_tweets
2. Extract and store embedded posts during sync

## Self-Check: PASSED

- [x] tests/test_migrations.py modified with TestMigrateToV6 class (6 tests)
- [x] tests/test_embedded_posts_repository.py created (5 tests)
- [x] tests/test_sync_service.py modified with TestEmbeddedPostsSync class (5 tests)
- [x] All 16 tests FAIL (expected for TDD RED phase)
- [x] Commits exist: 5405438, 93e7d94, aff853d