# Phase 13: LAN Network Access - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable web server binding to LAN IP for mobile device access. Users run `xbm web --lan` and the server binds to all interfaces (0.0.0.0) with mkcert-generated certificates. Mobile browsers can access the web app without certificate warnings after CA installation (Phase 12 delivered the platform guides).

This phase delivers:
- `--lan` flag on `xbm web` command
- Server binds to 0.0.0.0 when flag is used
- LAN certificate selection for HTTPS
- Startup URL display (localhost + LAN)
- Clear error handling for missing certificates

**Out of scope:**
- Certificate generation (Phase 12 complete)
- Platform guides for CA installation (Phase 12 complete)
- DNS hostname setup (e.g., mybookmarks.local)
- Auto-renewal of certificates

</domain>

<decisions>
## Implementation Decisions

### Network Binding
- **D-01:** Dual binding mode - bind to 0.0.0.0 when `--lan` flag used, making server accessible from both localhost and LAN IP simultaneously
  - Simpler for users: one command works everywhere
  - No separate server instances needed
  - Rationale: 0.0.0.0 binds all interfaces, localhost traffic still works

### URL Display
- **D-02:** Display both URLs after startup with clear labels
  - Local URL: `https://localhost:8000`
  - LAN URL: `https://192.168.1.x:8000` (detected via `get_lan_ip()`)
  - Use Rich Panel with both URLs shown
  - Rationale: Users can copy whichever URL is convenient for their device

### Certificate Handling
- **D-03:** Block startup if certificates missing when `--lan` used
  - Fail with Rich Panel error message
  - Include `xbm lan-cert --generate` command in error output
  - Do NOT auto-generate or fall back to self-signed (user must intentionally generate)
  - Rationale: Clear feedback, intentional user action required

### Error Format
- **D-04:** Rich Panel with colored border for error messages
  - Matches existing CLI style from Phase 12
  - Shows actionable command in error output
  - Rationale: Consistency with `lan-cert` command error handling

### Claude's Discretion
- Exact Panel content and formatting
- Console output styling and colors
- LAN IP detection error handling (when `get_lan_ip()` returns None)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — NET-01, NET-02, NET-03 (network binding requirements)
- `.planning/REQUIREMENTS.md` §PLAT-01 through PLAT-05 — Platform guides (delivered in Phase 12)

### Prior Phase Context
- `.planning/phases/12-certificate-management/12-CONTEXT.md` — Certificate generation, LAN IP detection, platform guides
- `.planning/phases/06-web-foundation/06-CONTEXT.md` — Web server startup, HTTPS configuration

### Existing Code
- `src/cli/main.py:1883` — Current `web` command implementation
- `src/web/app.py` — FastAPI app creation
- `src/web/lan_certs.py` — Certificate utilities (mkcert integration, LAN IP detection)
- `src/config/settings.py:74-77` — LAN settings (`lan_enabled`, `lan_cert_path`, `lan_key_path`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`get_lan_ip()`** — Already implemented in `lan_certs.py`, returns LAN IP address
- **`check_mkcert_installed()`** — Already implemented, validates mkcert availability
- **`get_certificate_info()`** — Returns certificate metadata including existence check
- **Settings.lan_cert_path / lan_key_path** — Already defined in settings.py
- **Rich Panel error pattern** — Established in Phase 12 `lan-cert` command

### Established Patterns
- **CLI command structure:** Typer commands with Rich Console output
- **Settings pattern:** Pydantic Settings with defaults
- **Certificate storage:** `data/lan.crt` and `data/lan.key`
- **Error messages:** Rich Panel with colored border, actionable commands

### Integration Points
- **`src/cli/main.py:web()`** — Add `--lan` boolean flag option
- **`src/cli/main.py:run_server`** — Conditional binding: `host = "0.0.0.0" if lan else "127.0.0.1"`
- **`src/cli/main.py`** — Certificate check: use `get_certificate_info()` before server start
- **Console output** — Display both localhost and LAN URLs in startup Panel

</code_context>

<specifics>
## Specific Ideas

- Console output should show both URLs clearly:
  ```
  Local: https://localhost:8000
  LAN:   https://192.168.1.100:8000
  ```
- Error message when certificates missing:
  ```
  Run 'xbm lan-cert --generate' first
  ```
- Follow existing Rich Panel styling from Phase 12

</specifics>

<deferred>
## Deferred Ideas

- **DNS hostname (mybookmarks.local):** Requires mDNS/Bonjour setup, defer to future milestone
- **Auto-detect LAN IP changes:** Manual `--generate --force` sufficient for now
- **IPv6 binding:** Certificates include ::1 but explicit IPv6 binding deferred
- **Auto-start server on LAN:** User must explicitly use `--lan` flag

</deferred>

---
*Phase: 13-lan-network-access*
*Context gathered: 2026-06-08*