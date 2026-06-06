---
phase: 9
slug: web-display
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_web_browse.py -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_web_browse.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | WEB-07 | — | N/A | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_quote_tweet_display -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | WEB-08 | — | N/A | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_retweet_display -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | WEB-09 | — | N/A | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_embedded_media_display -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | WEB-10 | — | N/A | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_unavailable_placeholder -x` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 3 | WEB-07 | — | N/A | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_quote_tweet_api_response -x` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 3 | WEB-08 | — | N/A | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_retweet_api_response -x` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 4 | WEB-07, WEB-08, WEB-09, WEB-10 | T-09-01 | Jinja2 auto-escape for user content | integration | `pytest tests/test_web_browse.py::TestEmbeddedPosts::test_no_xss_in_embedded -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_web_browse.py::TestEmbeddedPosts` — test class for embedded post rendering
- [ ] Mock data: quote posts, retweet posts, unavailable posts in test fixtures
- [ ] Test: quote tweet shows user text + nested card with attribution
- [ ] Test: retweet shows attribution header + original content
- [ ] Test: unavailable shows placeholder with author if known
- [ ] Test: embedded media displays in adaptive grid
- [ ] Test: XSS prevention in embedded post content

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual card nesting on mobile | WEB-07 | Responsive breakpoints need visual inspection | Open `/browse` on mobile viewport, verify quote cards nest correctly |
| Lightbox close on click outside | WEB-09 | UI interaction requires manual verification | Click image to expand, click outside lightbox to close |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending