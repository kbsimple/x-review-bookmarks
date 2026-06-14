---
phase: 08-storage-foundation
plan: 01
subsystem: storage
tags: [schema, migration, x-client, referenced-tweets]
requires: ["08-00"]
provides: [schema-v6-migration, embedded-posts-table, post-type-column, x-client-referenced-tweets]
affects: []
tech_stack:
  added: []
  patterns: [schema-migration, try-except-idempotency, dictionary-lookup]
key_files:
  created: []
  modified:
    - src/db/schema.py
    - src/db/migrations.py
    - src/api/x_client.py
decisions:
  - SCHEMA_V6_MIGRATION constant with embedded_posts table definition
  - try/except pattern for ALTER TABLE idempotency (SQLite limitation)
  - referenced_tweets dictionary with str(t.id) keys for O(1) lookup
duration_seconds: 180
completed_at: "2026-06-04T09:10:00Z"
---

# Phase 08 Plan 01: Schema V6 Migration and XClient Extensions Summary

## One-liner

Implemented schema migration V6 for embedded posts and extended XClient to fetch referenced tweet content via expansions.

## What Was Done

### Task 1: Add SCHEMA_V6_MIGRATION to schema.py

Added schema migration constant following existing V5 pattern:

- Created `embedded_posts` table with columns per D-01:
  - `x_post_id TEXT PRIMARY KEY`
  - `created_at TIMESTAMP NOT NULL`
  - `text TEXT NOT NULL`
  - `author_id TEXT NOT NULL`
  - `author_username TEXT NOT NULL`
  - `author_display_name TEXT`
  - `media_urls TEXT` (JSON array)
  - `link_urls TEXT` (JSON array)
  - `available INTEGER DEFAULT 1` (Boolean: 1=available, 0=deleted/protected)
- Updated `get_schema_version()` to return "v6"

**Commit:** `ebf6271`

### Task 2: Add migrate_to_v6 to migrations.py

Implemented migration function following existing pattern:

- Check `current_version >= 6` for early return (idempotency)
- Execute `SCHEMA_V6_MIGRATION` with `conn.executescript()`
- Add `post_type TEXT DEFAULT 'original'` column with try/except (SQLite doesn't support IF NOT EXISTS)
- Add `embedded_post_id TEXT` column with try/except
- Set `PRAGMA user_version = 6`
- Added `migrate_to_v6` to `run_migrations()` call chain
- Exported `migrate_to_v6` in `__all__`

**Commit:** `e9b91db`

### Task 3: Extend XClient EXPANSIONS and TWEET_FIELDS

Modified XClient for referenced tweets expansion:

- Extended `EXPANSIONS` constant:
  ```
  author_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.author_id,referenced_tweets.id.attachments.media_keys
  ```
- Extended `TWEET_FIELDS` to include `referenced_tweets`
- Added `referenced_tweets: dict[str, Any]` field to `BookmarkFetchResult`
- Populated `referenced_tweets` from `includes.tweets` in `fetch_bookmarks()`

**Commit:** `9391a34`

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

| Test Suite | Result | Notes |
|------------|--------|-------|
| TestMigrateToV6 (6 tests) | 6 passed | All schema migration tests pass |
| XClient extensions | Verified | Manual verification of constants and dataclass |

Note: `TestEmbeddedPostsSync` tests require EmbeddedPostsRepository (plan 02) and SyncService modifications (plan 03). These tests will pass after those plans are implemented.

## Verification

- [x] `get_schema_version()` returns "v6"
- [x] `migrate_to_v6` function exists and is idempotent
- [x] `SCHEMA_V6_MIGRATION` creates embedded_posts table with all columns
- [x] `XClient.EXPANSIONS` contains referenced_tweets.id.*
- [x] `XClient.TWEET_FIELDS` contains referenced_tweets
- [x] `BookmarkFetchResult` has referenced_tweets field

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| src/db/schema.py | +23/-3 | SCHEMA_V6_MIGRATION constant, get_schema_version() |
| src/db/migrations.py | +47/-2 | migrate_to_v6 function, run_migrations update |
| src/api/x_client.py | +6/-2 | EXPANSIONS, TWEET_FIELDS, BookmarkFetchResult |

## Requirements Coverage

| Requirement | Implementation |
|-------------|----------------|
| STR-01: Schema migration adds embedded_posts table | SCHEMA_V6_MIGRATION creates table |
| STR-02: Posts table gains post_type, embedded_post_id | migrate_to_v6 adds columns |
| (Partial) XClient can fetch referenced tweets | EXPANSIONS and TWEET_FIELDS extended |

## Next Steps

Plan 02 will implement:
1. `src/repositories/embedded_posts.py` with EmbeddedPostsRepository class
2. Upsert and get_by_id methods for embedded_posts table

Plan 03 will implement:
1. Update SyncService._store_tweet() to handle referenced_tweets
2. Extract and store embedded posts during sync
3. Create unavailable embedded posts for deleted/protected originals

## Self-Check: PASSED

- [x] src/db/schema.py contains SCHEMA_V6_MIGRATION constant
- [x] src/db/migrations.py contains migrate_to_v6 function
- [x] src/api/x_client.py contains extended EXPANSIONS
- [x] All 6 TestMigrateToV6 tests pass
- [x] Commits exist: ebf6271, e9b91db, 9391a34