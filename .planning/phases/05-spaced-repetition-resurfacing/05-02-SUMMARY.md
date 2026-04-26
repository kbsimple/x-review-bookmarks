---
phase: 05-spaced-repetition-resurfacing
plan: 02
subsystem: services
tags: [fsrs, spaced-repetition, scheduling, orchestration]

# Dependency graph
requires:
  - phase: 04-topic-organization
    provides: posts table, post_topics table for themed reviews
  - plan: 05-01
    provides: post_review_state table, ReviewStateRepository
provides:
  - ReviewScheduler service for interval calculation
  - ReviewService orchestration layer
affects: [05-03, 05-04]

# Tech tracking
tech-stack:
  added:
    - fsrs 3.1.0
  patterns: [tdd, fsrs-scheduling, service-layer]

key-files:
  created:
    - src/services/review_scheduler.py
    - src/services/review_service.py
    - tests/test_review_scheduler.py
    - tests/test_review_service.py
  modified:
    - src/services/__init__.py

key-decisions:
  - "Use FSRS Card.to_dict() + json serialization (no to_json method)"
  - "Card.from_dict requires 'due' field - use Card() defaults"
  - "Make valid fsrs_data via json.dumps(Card().to_dict()) in tests"
  - "Postpone caps days at 365 (1 year max)"

requirements-completed: [SPAC-01, SPAC-02]

# Metrics
duration: 11min
started: 2026-04-25T16:39:23Z
completed: 2026-04-25T16:50:25Z
tasks: 2
files_modified: 4

---

# Phase 05 Plan 02: ReviewScheduler & ReviewService Summary

**ReviewScheduler with FSRS Card state management and ReviewService orchestration layer for spaced repetition scheduling**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-25T16:39:23Z
- **Completed:** 2026-04-25T16:50:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Implemented ReviewScheduler with user-controlled scheduling intervals
- Implemented ReviewService to orchestrate repository and scheduler operations
- Added fsrs library for FSRS-4.5 Card state management
- Full test coverage (39 tests) for scheduler and service

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement ReviewScheduler with FSRS Card state management** - `1773cd2` (feat)
2. **Task 2: Implement ReviewService orchestration layer** - `c1f9a59` (feat)

## Files Created/Modified

- `src/services/review_scheduler.py` - ReviewScheduler class with INTERVALS and POSTPONE_INTERVALS constants
- `src/services/review_service.py` - ReviewService class for orchestration
- `src/services/__init__.py` - Added ReviewScheduler and ReviewService exports
- `tests/test_review_scheduler.py` - 27 tests for scheduler logic
- `tests/test_review_service.py` - 12 tests for service orchestration

## Decisions Made

- FSRS Card serialization uses `json.dumps(card.to_dict())` and `Card.from_dict(json.loads(data))` - the fsrs library does not have `to_json`/`from_json` methods
- Test fixtures use `make_fsrs_data()` helper to create valid Card JSON with required `due` field
- Postpone days are capped at 365 (T-05-05 mitigation)
- User choice validation raises ValueError for invalid choices (T-05-04 mitigation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FSRS Card serialization API mismatch**
- **Found during:** Task 1 test execution
- **Issue:** Plan specified `card.to_json()` and `Card.from_json()` but fsrs library uses `card.to_dict()` and `Card.from_dict()`
- **Fix:** Updated code to use `json.dumps(card.to_dict())` and `Card.from_dict(json.loads(data))`
- **Files modified:** src/services/review_scheduler.py, tests/test_review_scheduler.py
- **Commit:** 1773cd2

**2. [Rule 3 - Blocking] Missing 'due' field in Card deserialization**
- **Found during:** Task 1 test execution
- **Issue:** Card.from_dict requires 'due' field; test fixtures used invalid JSON
- **Fix:** Created `make_fsrs_data()` helper function that generates valid Card JSON with all required fields
- **Files modified:** tests/test_review_scheduler.py
- **Commit:** 1773cd2

## Verification Results

- All 39 scheduler/service tests pass
- All 419 project tests pass
- FSRS library import works: `from fsrs import Card`
- Interval constants match D-03: fresh=3d, soon=14d, later=60d
- Postpone intervals match D-09: 1d, 3d, 1w, 2w, 1m, 3m

## User Setup Required

Run `pip install fsrs` before using the scheduler (already installed in development environment).

## Next Phase Readiness

- ReviewScheduler ready for CLI integration (05-03)
- ReviewService ready for `xbm due`, `xbm review`, `xbm stats` commands
- FSRS Card state tracking functional for future algorithm enhancement

## Self-Check: PASSED

- All created files verified: src/services/review_scheduler.py, src/services/review_service.py, tests/test_review_scheduler.py, tests/test_review_service.py
- All commits verified: 1773cd2 (Task 1), c1f9a59 (Task 2)
- All 419 tests passing
- fsrs package installed and importable

---
*Phase: 05-spaced-repetition-resurfacing*
*Completed: 2026-04-25*