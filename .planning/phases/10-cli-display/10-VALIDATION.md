---
phase: 10
slug: cli-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | None — tests use CliRunner directly |
| **Quick run command** | `pytest tests/test_cli_display.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cli_display.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-00-01 | 00 | 0 | CLI-06 | — | N/A | unit | `pytest tests/test_cli_display.py::test_quote_tweet_rendering -x` | ❌ W0 | ⬜ pending |
| 10-00-02 | 00 | 0 | CLI-06 | — | N/A | unit | `pytest tests/test_cli_display.py::test_quote_attribution -x` | ❌ W0 | ⬜ pending |
| 10-00-03 | 00 | 0 | CLI-07 | — | N/A | unit | `pytest tests/test_cli_display.py::test_retweet_header -x` | ❌ W0 | ⬜ pending |
| 10-00-04 | 00 | 0 | CLI-07 | — | N/A | unit | `pytest tests/test_cli_display.py::test_retweet_content -x` | ❌ W0 | ⬜ pending |
| 10-00-05 | 00 | 0 | CLI-08 | — | N/A | unit | `pytest tests/test_cli_display.py::test_embedded_media_urls -x` | ❌ W0 | ⬜ pending |
| 10-00-06 | 00 | 0 | CLI-08 | — | N/A | unit | `pytest tests/test_cli_display.py::test_unavailable_placeholder -x` | ❌ W0 | ⬜ pending |
| 10-01-01 | 01 | 1 | CLI-07 | — | N/A | unit | `pytest tests/test_cli_display.py::test_retweet_rendering -x` | ✅ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | CLI-06 | — | N/A | unit | `pytest tests/test_cli_display.py::test_quote_rendering -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_display.py` — test scaffolding for all CLI-06, CLI-07, CLI-08 behaviors
- [ ] `tests/conftest.py` — fixtures for quote tweet, retweet, unavailable post dicts
- [ ] Test fixtures for `post_type='quote'` with embedded_post
- [ ] Test fixtures for `post_type='retweet'` with embedded_post
- [ ] Test fixtures for `available=False` embedded_post

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual confirmation of nested Panel styling | CLI-06 | Terminal output visual inspection | Run `xbm browse` with quote tweet, verify nested Panel borders and colors |

*All core behaviors have automated verification. Visual inspection optional.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending