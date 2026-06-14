---
phase: 15
slug: oembed-rich-embeds
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `pytest.ini` |
| **Quick run command** | `venv/bin/python -m pytest tests/test_oembed_service.py tests/test_static_export_service.py -q` |
| **Full suite command** | `venv/bin/python -m pytest --tb=short -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `venv/bin/python -m pytest tests/test_oembed_service.py tests/test_static_export_service.py -x --tb=short`
- **After every plan wave:** Run `venv/bin/python -m pytest --tb=short -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Requirement Verification Map

| Requirement | Description | Test Type | Automated Command | Wave |
|-------------|-------------|-----------|-------------------|------|
| OEMBED-01 | `xbm export-static --rich-embeds` fetches and stores `oembed_html` | unit | `pytest tests/test_static_export_service.py::TestRichEmbeds` | 1 |
| OEMBED-02 | Deleted/protected posts get `oembed_html: null` | unit | `pytest tests/test_static_export_service.py::TestRichEmbeds::test_rich_embeds_adds_oembed_html_to_posts_json` | 1 |
| OEMBED-03 | Viewer renders oEmbed HTML as Twitter widget | manual-only | n/a — JS inline in Python string, no browser test infra | n/a |
| OEMBED-04 | Posts without `oembed_html` render with existing card layout unchanged | unit | `pytest tests/test_static_export_service.py::TestRichEmbeds::test_no_rich_embeds_omits_oembed_html_field` | 1 |

---

## Wave 1 Requirements

- [ ] `tests/test_oembed_service.py` — new file, 5 cases (success/404/error/fetch_all/progress)
- [ ] `TestRichEmbeds` in `tests/test_static_export_service.py` — 3 cases (OEMBED-01, OEMBED-02, OEMBED-04)
- [ ] Guard bug fixed: `if oembed_map:` in `_write_posts_json` (required for OEMBED-04 test)

---

## Success Criteria Coverage

| Success Criterion | Covered By | Type |
|-------------------|------------|------|
| export-static --rich-embeds stores oembed_html in posts.json | TestRichEmbeds.test_rich_embeds_adds_oembed_html_to_posts_json | unit |
| Deleted/protected posts → oembed_html: null | TestRichEmbeds.test_rich_embeds_adds_oembed_html_to_posts_json (post_002 → None) | unit |
| Default (no --rich-embeds) → no oembed_html field | TestRichEmbeds.test_no_rich_embeds_omits_oembed_html_field | unit |
| Viewer renders native Twitter widget | MANUAL — open exported index.html via Netlify, confirm blockquote renders as widget | manual |
| netlify-deploy skill accepts "deploy with rich embeds" | MANUAL — confirm SKILL.md contains trigger phrase and correct command | file check |

---

## Known Manual-Only Items

**OEMBED-03 — Viewer rendering:** The Twitter widget rendering requires a browser and live CDN access. The blockquote HTML is verified present in posts.json by TestRichEmbeds; that the widget JS transforms it into a rich card is verified by deploying to Netlify and viewing the page.

No automated test coverage for viewer JS — it is inline JavaScript inside a Python string in `static_export.py` and there is no JS test infrastructure in this project.
