---
phase: 18
slug: background-prefetch
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-18
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_static_export_service.py -x -q` |
| **Full suite command** | `python -m pytest --tb=short -q` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_static_export_service.py -x -q`
- **After every plan wave:** Run `python -m pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 18-00-01 | 00 | 0 | PREFETCH-01,08 | N/A | string-grep (RED stub) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_schedule_prefetch_function_present -x` | ❌ W0 | ⬜ pending |
| 18-00-02 | 00 | 0 | PREFETCH-02 | N/A | string-grep (RED stub) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_prefetch_window_constants_present -x` | ❌ W0 | ⬜ pending |
| 18-00-03 | 00 | 0 | PREFETCH-04 | N/A | string-grep (RED stub) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_request_idle_callback_present -x` | ❌ W0 | ⬜ pending |
| 18-00-04 | 00 | 0 | PREFETCH-05 | N/A | string-grep (RED stub) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_prefetch_pool_hit_check_present -x` | ❌ W0 | ⬜ pending |
| 18-00-05 | 00 | 0 | PREFETCH-06 | N/A | string-grep (RED stub) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_clear_prefetch_pool_present -x` | ❌ W0 | ⬜ pending |
| 18-00-06 | 00 | 0 | PREFETCH-07 | N/A | string-grep (RED stub) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch::test_prefetch_pool_eviction_present -x` | ❌ W0 | ⬜ pending |
| 18-01-01 | 01 | 1 | PREFETCH-01–08 | N/A | string-grep (GREEN) | `pytest tests/test_static_export_service.py::TestIndexHtmlPrefetch -x` | ✅ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | PREFETCH-03 | N/A | string-grep (existing) | `pytest tests/test_static_export_service.py::TestRichEmbeds -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_static_export_service.py` — add `TestIndexHtmlPrefetch` class with RED stubs for PREFETCH-01, PREFETCH-02, PREFETCH-04, PREFETCH-05, PREFETCH-06, PREFETCH-07, PREFETCH-08

*Existing `TestRichEmbeds` and `TestIndexHtmlCarousel` cover PREFETCH-03 partially.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Twitter widget visibly pre-loaded (no blank/flash) when navigating to prefetched oEmbed post | PREFETCH-03 | Requires browser with live Netlify/Twitter CDN | Run `xbm export-static --rich-embeds`, deploy, navigate to oEmbed post, press Next rapidly — verify no skeleton flash on posts within prefetch window |
| First-post render not delayed | PREFETCH-04 | Requires browser performance measurement | Open viewer, verify first post appears before any prefetch activity in DevTools Performance timeline |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
