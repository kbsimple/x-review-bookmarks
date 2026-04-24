---
phase: 03-search-notes-and-import-export
plan: 01
subsystem: database

# Dependency graph
requires:
  - phase: 02-bookmark-fetch-and-storage
    provides: Posts table schema, PostsRepository CRUD operations
provides:
  - FTS5 virtual table (posts_fts) for full-text search
  - note column on posts table for personal notes
  - link_status column for dead link tracking
  - Migration system with PRAGMA user_version tracking
  - PostsRepository methods: update_note(), update_link_status(), get_posts_with_links(), get_posts_exclude_dead_links()
  - Wave 0 test scaffolds for search, export, and link checker services
affects:
  - 03-search-notes-and-import-export (plans 02-06)
  - All phases that query posts table

# Tech tracking
tech-stack:
  added:
    - SQLite FTS5 (built-in, used for full-text search)
  patterns:
    - PRAGMA user_version for schema migrations
    - FTS5 external content table pattern with sync triggers
    - Repository pattern extended for new columns

key-files:
  created:
    - src/db/migrations.py - Migration system with version tracking
    - tests/test_migrations.py - Migration tests (25 tests)
    - tests/test_search_service.py - Wave 0 scaffold for search tests
    - tests/test_export_service.py - Wave 0 scaffold for export tests
    - tests/test_link_checker.py - Wave 0 scaffold for link checker tests
  modified:
    - src/db/schema.py - SCHEMA_V3_MIGRATION constant
    - src/db/__init__.py - Export migrations, call run_migrations()
    - src/repositories/posts.py - New methods for note, link_status
    - tests/test_db.py - Updated schema version test
    - tests/test_posts_repository.py - New tests for note/link_status

key-decisions:
  - "Used SCHEMA_V3_MIGRATION constant for FTS5/triggers, ALTER TABLE in migrations.py"
  - "FTS5 uses external content table pattern with sync triggers"
  - "PRAGMA user_version for idempotent migration tracking"
  - "link_status default 'unchecked', supports 'ok', 'dead', 'error', or ISO timestamp"

patterns-established:
  - "Migration pattern: Check user_version, apply changes, set user_version"
  - "FTS5 pattern: Virtual table + INSERT/UPDATE/DELETE triggers for sync"
  - "Repository extension pattern: Add methods for new columns without breaking existing code"

requirements-completed:
  - SRCH-01
  - NOTE-01
  - MAINT-01

# Metrics
duration: 15min
completed: 2026-04-23
---

# Phase 3 Plan 01: FTS5 Schema and Repository Extensions Summary

**SQLite FTS5 full-text search with sync triggers, note/link_status columns, and Wave 0 test scaffolds for Phase 3 services**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-23T00:00:00Z
- **Completed:** 2026-04-23T00:15:00Z
- **Tasks:** 5
- **Files modified:** 11

## Accomplishments
- FTS5 virtual table (posts_fts) with external content table pattern and sync triggers
- Schema migration system using PRAGMA user_version for idempotent v2->v3 upgrades
- note and link_status columns added to posts table
- PostsRepository extended with update_note(), update_link_status(), get_posts_with_links(), get_posts_exclude_dead_links()
- Wave 0 test scaffolds created for search, export, and link checker services (27 tests)

## Task Commits

Each task was committed atomically:

1. **Tasks 1-3: FTS5 schema and migrations** - `7fa0efb` (feat)
   - Created SCHEMA_V3_MIGRATION with FTS5 virtual table and triggers
   - Created migrations.py with PRAGMA user_version tracking
   - Updated init_database() to run migrations automatically
2. **Task 4: PostsRepository extensions** - `58a9c9f` (feat)
   - Added update_note() and update_link_status() methods
   - Added get_posts_with_links() and get_posts_exclude_dead_links() methods
   - Updated _row_to_dict() to include note and link_status
3. **Task 5: Wave 0 test scaffolds** - `b47ef8e` (test)
   - Created test_search_service.py (6 test stubs)
   - Created test_export_service.py (9 test stubs)
   - Created test_link_checker.py (12 test stubs)

## Files Created/Modified
- `src/db/schema.py` - SCHEMA_V3_MIGRATION constant with FTS5 virtual table and triggers
- `src/db/migrations.py` - Migration system with get_schema_version_int(), migrate_to_v3(), run_migrations()
- `src/db/__init__.py` - Updated to export migrations and call run_migrations() in init_database()
- `src/repositories/posts.py` - Extended with note/link_status methods
- `tests/test_migrations.py` - 25 tests for migration system
- `tests/test_db.py` - Updated test for schema version
- `tests/test_posts_repository.py` - 8 new tests for note/link_status (15 total)
- `tests/test_search_service.py` - Wave 0 scaffold (6 test stubs)
- `tests/test_export_service.py` - Wave 0 scaffold (9 test stubs)
- `tests/test_link_checker.py` - Wave 0 scaffold (12 test stubs)

## Decisions Made
- Used SCHEMA_V3_MIGRATION constant for FTS5/triggers, while ALTER TABLE statements are in migrations.py (SQLite doesn't support ALTER TABLE IF NOT EXISTS)
- FTS5 uses external content table pattern (content='posts') to avoid data duplication
- Sync triggers (posts_ai, posts_ad, posts_au) keep FTS5 index synchronized with posts table
- PRAGMA user_version provides clean migration version tracking
- link_status supports: 'ok', 'dead', 'error', 'unchecked', or ISO timestamp for re-check scheduling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test fixture temp_db_with_schema needed updating to include note and link_status columns for new tests
- Fixed by adding columns to the CREATE TABLE statement in the fixture

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- FTS5 infrastructure ready for search service implementation (Plan 02)
- note column ready for note CLI command (Plan 03)
- link_status column ready for link checker service (Plan 04)
- Wave 0 test scaffolds ready for Wave 2 implementation

---
*Phase: 03-search-notes-and-import-export*
*Plan: 01*
*Completed: 2026-04-23*

## Self-Check: PASSED

- All created files exist (src/db/migrations.py, tests/test_migrations.py, tests/test_search_service.py, tests/test_export_service.py, tests/test_link_checker.py)
- All commits exist (7fa0efb, 58a9c9f, b47ef8e)
- All 54 tests pass