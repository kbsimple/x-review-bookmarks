---
phase: 5
slug: spaced-repetition-resurfacing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml (tool.pytest) |
| **Quick run command** | `pytest tests/ -x -v` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -v`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SPAC-01 | T-5-01 / — | Calculate next review date from publication date | unit | `pytest tests/test_review_scheduler.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | SPAC-01 | — | FSRS Card state serialization | unit | `pytest tests/test_review_scheduler.py::test_fsrs_serialization -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | SPAC-02 | — | Get due posts query | unit | `pytest tests/test_review_state_repository.py::test_get_due_posts -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | SPAC-04 | — | Themed review filter by topic | unit | `pytest tests/test_review_state_repository.py::test_get_due_by_topic -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | D-12 | — | Get review statistics | unit | `pytest tests/test_review_state_repository.py::test_get_stats -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | SPAC-03 | — | `xbm due` command output | integration | `pytest tests/test_cli.py::test_due_command -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 3 | CLI-02 | — | `xbm review` interactive session | integration | `pytest tests/test_cli.py::test_review_command -x` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 3 | D-05 | — | Note display at top during review | integration | `pytest tests/test_cli.py::test_review_note_display -x` | ❌ W0 | ⬜ pending |
| 05-03-04 | 03 | 3 | D-07 | — | User choice scheduling intervals | unit | `pytest tests/test_review_scheduler.py::test_schedule_intervals -x` | ❌ W0 | ⬜ pending |
| 05-03-05 | 03 | 3 | D-09 | — | Postpone intervals | unit | `pytest tests/test_review_scheduler.py::test_postpone -x` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 4 | D-12 | — | `xbm stats` command | integration | `pytest tests/test_cli.py::test_stats_command -x` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 4 | D-13 | — | `xbm reset` command | integration | `pytest tests/test_cli.py::test_reset_command -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_review_state_repository.py` — covers SPAC-01, SPAC-02, SPAC-04 repository operations
- [ ] `tests/test_review_scheduler.py` — covers SPAC-01 scheduling logic, D-07 intervals, D-09 postpone
- [ ] `tests/test_cli.py` additions — covers SPAC-03, CLI-02, D-12, D-13 CLI commands
- [ ] `tests/conftest.py` updates — add fixtures for review_state table
- [ ] Install dependencies: `pip install fsrs apscheduler`
- [ ] `src/db/schema.py` — SCHEMA_V5_MIGRATION for post_review_state table

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive review UX | CLI-02 | Interactive prompts require terminal | Run `xbm review` and verify note display, metadata, choice prompts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending