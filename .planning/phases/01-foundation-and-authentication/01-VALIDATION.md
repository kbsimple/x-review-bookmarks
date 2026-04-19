---
phase: 01
slug: foundation-and-authentication
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pytest.ini (Wave 0 creates) |
| **Quick run command** | `pytest tests/ -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | AUTH-01 | T-01-01 | PKCE flow uses state parameter | unit | `pytest tests/test_oauth.py::test_get_authorization_url -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | AUTH-01 | T-01-02 | Callback server binds 127.0.0.1 only | unit | `pytest tests/test_oauth.py::test_callback_server_binding -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | AUTH-02 | T-01-03 | Tokens stored with 0600 permissions | unit | `pytest tests/test_oauth.py::test_token_file_permissions -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | AUTH-02 | — | Token refresh works on 401 | unit | `pytest tests/test_oauth.py::test_refresh_expired_token -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | AUTH-03 | — | Expired token returns clear error | unit | `pytest tests/test_oauth.py::test_handle_expired_token -x` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 1 | AUTH-03 | — | Invalid token returns clear error | unit | `pytest tests/test_oauth.py::test_handle_invalid_token -x` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 2 | STOR-01 | — | Database initialized with WAL mode | unit | `pytest tests/test_db.py::test_wal_mode_enabled -x` | ❌ W0 | ⬜ pending |
| 01-04-02 | 04 | 2 | STOR-02 | — | Foreign keys enforced on connection | unit | `pytest tests/test_db.py::test_foreign_keys_enabled -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_oauth.py` — stubs for AUTH-01, AUTH-02, AUTH-03
- [ ] `tests/test_db.py` — stubs for STOR-01, STOR-02
- [ ] `tests/conftest.py` — shared fixtures (mock_auth, temp_db, mock_settings)
- [ ] `pytest.ini` — pytest configuration
- [ ] Framework install: `pip install pytest pytest-asyncio`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OAuth callback in browser | AUTH-01 | Requires user interaction with X login | Run `python -m src.cli.main auth`, click URL, authorize in browser, verify success message |
| Token file location | AUTH-02 | Configurable via settings | Verify `data/tokens.json` created after first auth |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending