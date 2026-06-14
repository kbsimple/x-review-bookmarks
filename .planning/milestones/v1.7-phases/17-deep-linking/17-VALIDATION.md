---
phase: 17
slug: deep-linking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-14
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_static_export_service.py -q` |
| **Full suite command** | `python3 -m pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_static_export_service.py -q`
- **After every plan wave:** Run `python3 -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| DL-01 | 00 | 0 | DL-01 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_share_btn_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-02 | 00 | 0 | DL-02 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_copy_deep_link_function_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-03 | 00 | 0 | DL-03 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_clipboard_write_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-04 | 00 | 0 | DL-04 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_hash_detection_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-05 | 00 | 0 | DL-05 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_post_hash_prefix_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-06 | 00 | 0 | DL-06 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_deep_link_mode_flag_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-07 | 00 | 0 | DL-07 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_deep_link_mode_css_class_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-08 | 00 | 0 | DL-08 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_xbm_home_btn_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-09 | 00 | 0 | DL-09 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_go_home_function_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-10 | 00 | 0 | DL-10 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_show_deep_link_error_present -x` | ❌ Wave 0 | ⬜ pending |
| DL-11 | 00 | 0 | DL-11 | unit (string grep) | `pytest tests/test_static_export_service.py::TestIndexHtmlDeepLink::test_xbm_home_text_present -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_static_export_service.py` — add `TestIndexHtmlDeepLink` class with 11 stub methods (all failing RED initially: `test_share_btn_present`, `test_copy_deep_link_function_present`, `test_clipboard_write_present`, `test_hash_detection_present`, `test_post_hash_prefix_present`, `test_deep_link_mode_flag_present`, `test_deep_link_mode_css_class_present`, `test_xbm_home_btn_present`, `test_go_home_function_present`, `test_show_deep_link_error_present`, `test_xbm_home_text_present`)

*Existing pytest infrastructure and conftest cover all other aspects — only the new class is needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Clipboard copy works in browser | DL-01/DL-02 | `navigator.clipboard` requires HTTPS/user gesture, untestable in pytest | Open Netlify deploy, click share icon, verify clipboard, paste to confirm URL |
| Deep link navigation in browser | DL-03/DL-04 | Browser hash routing requires real browser runtime | Open `index.html#post-{real_id}`, verify carousel with XBM Home button |
| "Post not found" graceful error | DL-10 | Requires rendering in browser | Open `index.html#post-fake999`, verify error message with XBM Home link |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
