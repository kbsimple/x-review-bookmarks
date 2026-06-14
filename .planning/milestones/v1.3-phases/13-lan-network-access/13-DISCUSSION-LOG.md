# Phase 13: LAN Network Access - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 13-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08T06:55:00Z
**Phase:** 13-lan-network-access
**Areas discussed:** Network Binding, URL Display, Certificate Handling, Error Format

---

## Network Binding

| Option | Description | Selected |
|--------|-------------|----------|
| Dual binding | Binds to 0.0.0.0 - both localhost and LAN IP work simultaneously | ✓ |
| LAN-only binding | Only binds to LAN IP, localhost requires separate server instance | |

**User's choice:** Dual binding (0.0.0.0)
**Notes:** Simpler for users - one command works everywhere. No separate server instances needed.

---

## URL Display

| Option | Description | Selected |
|--------|-------------|----------|
| Both URLs displayed | Show Local: https://localhost:8000 and LAN: https://192.168.1.x:8000 with clear labels | ✓ |
| LAN URL only | Only show the LAN URL to keep output minimal | |
| Local URL only | Show only localhost URL, user can check their IP separately | |

**User's choice:** Both URLs displayed with clear labels
**Notes:** Users can copy whichever URL is convenient for their device. Use Rich Panel for consistency.

---

## Certificate Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Block startup | Fail with 'Run xbm lan-cert --generate first' message before server starts | ✓ |
| Warn but continue | Show warning but start with self-signed localhost certs as fallback | |
| Auto-generate | Generate certs automatically if missing using lan_certs module | |

**User's choice:** Block startup with clear error message
**Notes:** Clear feedback, intentional user action required. Do NOT auto-generate or fall back.

---

## Error Format

| Option | Description | Selected |
|--------|-------------|----------|
| Rich Panel | Rich Panel with colored border, shows 'xbm lan-cert --generate' command ready to copy | ✓ |
| Plain text | Plain text error message | |

**User's choice:** Rich Panel with colored border
**Notes:** Matches existing CLI style from Phase 12. Shows actionable command in error output.

---

## Claude's Discretion

- Exact Panel content and formatting
- Console output styling and colors
- LAN IP detection error handling (when `get_lan_ip()` returns None)

## Deferred Ideas

- DNS hostname (mybookmarks.local) — requires mDNS/Bonjour setup, defer to future milestone
- Auto-detect LAN IP changes — manual `--generate --force` sufficient for now
- IPv6 binding — certificates include ::1 but explicit IPv6 binding deferred
- Auto-start server on LAN — user must explicitly use `--lan` flag