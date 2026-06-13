---
phase: 14
slug: static-export
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_static_export_service.py -x --tb=short` |
| **Full suite command** | `.venv/bin/python -m pytest --tb=short -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_static_export_service.py -x --tb=short`
- **After every plan wave:** Run `.venv/bin/python -m pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-00-01 | 00 | 0 | EXPORT-01,02,03,04 | unit | `pytest tests/test_static_export_service.py -x --tb=short` | ❌ W0 | ⬜ pending |
| 14-01-01 | 01 | 1 | EXPORT-01 | unit | `pytest tests/test_static_export_service.py::TestJsonFiles -x` | ✅ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | EXPORT-03 | unit | `pytest tests/test_static_export_service.py::TestSearchIndex -x` | ✅ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | EXPORT-02 | unit | `pytest tests/test_static_export_service.py::TestIndexHtml -x` | ✅ W0 | ⬜ pending |
| 14-02-02 | 02 | 2 | EXPORT-04 | unit | `pytest tests/test_static_export_service.py::TestNetlifyToml -x` | ✅ W0 | ⬜ pending |
| 14-03-01 | 03 | 3 | EXPORT-01,02,03,04 | integration | `pytest tests/test_export_static_cli.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_static_export_service.py` — stubs for EXPORT-01 through EXPORT-04
- [ ] `tests/test_export_static_cli.py` — CLI integration test stubs
- [ ] `tests/conftest.py` — confirm existing fixtures usable (in_memory_db, sample_post)

---

## Success Criteria Coverage

| Success Criterion | Test Coverage | Notes |
|-------------------|---------------|-------|
| `xbm export-static` generates JSON files (posts, tags, topics, review_state, search-index) | `TestJsonFiles` | All 5 files created, correct schema |
| Export includes pre-built search index | `TestSearchIndex` | Denormalized fields, created_at_ts present |
| Static web app displays posts with client-side search | `TestIndexHtml` | index.html contains expected JS patterns |
| netlify.toml present with cache headers | `TestNetlifyToml` | Content assertions on toml file |
| CLI command completes without error | `test_export_static_cli.py` | Exit code 0, output directory created |
