---
phase: 05-spaced-repetition-resurfacing
plan: 03
subsystem: cli
tags: [cli, due-command, review-command, spaced-repetition, interactive]

# Dependency graph
requires:
  - phase: 05-02
    provides: ReviewService, ReviewScheduler
  - phase: 04-topic-organization
    provides: TopicsRepository, topic filtering
provides:
  - `xbm due` command for viewing due posts
  - `xbm review` command for interactive review sessions
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [tdd, typer-cli, rich-output, interactive-prompt]

key-files:
  created: []
  modified:
    - src/cli/main.py
    - tests/test_cli.py

key-decisions:
  - "Table format for `xbm due` with truncated content (50 chars)"
  - "Interactive one-at-a-time review session for `xbm review`"
  - "Note displayed in yellow Panel at top if present"
  - "Five scheduling choices: fresh (3d), soon (2w), later (2m), skip, postpone"

requirements-completed: [SPAC-03, SPAC-04, CLI-02]

# Metrics
duration: 15min
started: 2026-04-25T16:52:07Z
completed: 2026-04-25T17:07:00Z
tasks: 2
files_modified: 2

---

# Phase 05 Plan 03: Due and Review CLI Commands Summary

**`xbm due` command for viewing due posts and `xbm review` command for interactive review sessions**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-25T16:52:07Z
- **Completed:** 2026-04-25T17:07:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Implemented `xbm due` command with table output and --topic flag (SPAC-03, D-04, D-08)
- Implemented `xbm review` command with interactive session (CLI-02, D-05, D-06, D-07, D-10)
- Added --topic flag for themed reviews (SPAC-04)
- Added --days flag for custom postpone duration
- Full test coverage (18 tests total for both commands)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement `xbm due` command** - `018401c` (feat)
2. **Task 2: Implement `xbm review` command** - `1d645a0` (feat)

## Files Modified

- `src/cli/main.py` - Added `due` and `review` CLI commands
- `tests/test_cli.py` - Added TestDueCommand (7 tests) and TestReviewCommand (11 tests)

## Decisions Made

- Table format for `xbm due` with columns: #, Author, Content Preview, Topics, Due
- Content truncated to 50 characters in preview
- Interactive one-at-a-time review session for `xbm review`
- Note displayed in yellow Panel at top if present (D-05)
- Five scheduling choices: fresh (1), soon (2), later (3), skip (s), postpone (p)
- Default choice is 'soon' (2 weeks) for prompt
- --topic flag uses TopicsRepository.get_topic_by_name for resolution
- Error message for topic not found

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- All 103 CLI tests pass
- `xbm due` command shows table format (D-04)
- `xbm due --topic` filters by topic name (D-08, SPAC-04)
- `xbm review` shows note at top (D-05)
- `xbm review` shows metadata (D-06)
- `xbm review` prompts for scheduling choice (D-07)
- All scheduling choices update review state correctly
- Postpone with --days works
- Skip option available

## Self-Check: PASSED

- All created files verified: src/cli/main.py modified
- All commits verified: 018401c (Task 1), 1d645a0 (Task 2)
- All 103 tests passing
- `due` command works as expected
- `review` command works as expected

---
*Phase: 05-spaced-repetition-resurfacing*
*Completed: 2026-04-25*