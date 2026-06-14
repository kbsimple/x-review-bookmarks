---
phase: 3
slug: search-notes-and-import-export
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml (testpaths: tests, python_files: test_*.py) |
| **Quick run command** | `pytest tests/test_<module>.py -x` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_<module>.py -x`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SRCH-01, SRCH-02, SRCH-03 | T-3-01 | Parameterized FTS5 queries | unit | `pytest tests/test_search_service.py -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | NOTE-01, NOTE-02 | — | N/A | unit | `pytest tests/test_posts_repository.py -x` | ✅ extend | ⬜ pending |
| 03-03-01 | 03 | 2 | IMEX-01, IMEX-02, IMEX-03 | T-3-02 | Path validation, version check | unit | `pytest tests/test_export_service.py -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 2 | MAINT-01, MAINT-02 | T-3-03 | Timeout limits, URL validation | unit | `pytest tests/test_link_checker.py -x` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 3 | CLI-03 | — | N/A | integration | `pytest tests/test_cli.py::TestSearchCommand -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_search_service.py` — stubs for SRCH-01, SRCH-02, SRCH-03
- [ ] `tests/test_export_service.py` — stubs for IMEX-01, IMEX-02, IMEX-03
- [ ] `tests/test_link_checker.py` — stubs for MAINT-01
- [ ] `tests/test_cli.py::TestSearchCommand` — CLI integration test for search
- [ ] `tests/test_cli.py::TestNoteCommand` — CLI integration test for note
- [ ] `tests/test_cli.py::TestExportCommand` — CLI integration test for export
- [ ] `tests/test_cli.py::TestImportCommand` — CLI integration test for import
- [ ] `tests/test_cli.py::TestCheckLinksCommand` — CLI integration test for check-links
- [ ] Extend `tests/test_posts_repository.py` — add note and link_status column tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | All phase behaviors have automated verification. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending