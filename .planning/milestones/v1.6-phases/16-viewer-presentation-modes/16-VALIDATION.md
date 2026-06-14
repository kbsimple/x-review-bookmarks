---
phase: 16
slug: viewer-presentation-modes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `venv/bin/python -m pytest tests/test_static_export_service.py -x -q` |
| **Full suite command** | `venv/bin/python -m pytest --tb=short -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `venv/bin/python -m pytest tests/test_static_export_service.py -x -q`
- **After every plan wave:** Run `venv/bin/python -m pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | VIEWER-01..05 | unit (Wave 0 stubs) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel -x` | ❌ Wave 0 | ⬜ pending |
| 16-01-02 | 01 | 1 | VIEWER-01 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel::test_mode_switcher -x` | ❌ Wave 0 | ⬜ pending |
| 16-01-03 | 01 | 1 | VIEWER-02 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel::test_localstorage -x` | ❌ Wave 0 | ⬜ pending |
| 16-01-04 | 01 | 1 | VIEWER-03 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel::test_render_carousel -x` | ❌ Wave 0 | ⬜ pending |
| 16-01-05 | 01 | 1 | VIEWER-04 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel::test_keyboard_nav -x` | ❌ Wave 0 | ⬜ pending |
| 16-01-06 | 01 | 1 | VIEWER-05 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlCarousel::test_oembed_carousel -x` | ❌ Wave 0 | ⬜ pending |
| 16-01-07 | 01 | 1 | VIEWER-06 | unit (regression) | `pytest tests/test_static_export_service.py::TestIndexHtml -x` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_static_export_service.py::TestIndexHtmlCarousel` — stub class with failing assertions for VIEWER-01..05
- [ ] No new conftest fixtures required — `TestIndexHtmlCarousel` can call `StaticExportService._build_index_html()` directly (no DB connection needed)

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Carousel renders single post with prev/next nav | VIEWER-07 | Requires live browser; no JS test infra | Deploy to Netlify or open locally, export, switch to Carousel mode, verify single-post display |
| Keyboard Left/Right/Escape navigation works | VIEWER-08 | Requires keyboard events in real browser | Open viewer, switch to Carousel, press ArrowRight/ArrowLeft, verify navigation; press Escape, verify Stream mode |
| oEmbed renders inside carousel (Twitter widget) | VIEWER-09 | Requires external CDN and live DOM | Export with `--rich-embeds`, switch to Carousel, verify oEmbed posts show as Twitter widgets not bare blockquotes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
