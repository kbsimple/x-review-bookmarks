# Phase 12: Certificate Management - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Users can check, generate, and manage LAN SSL certificates via CLI for mobile device access to the web app. This phase delivers the `xbm lan-cert` command with status checking, certificate generation, and platform-specific guidance.

</domain>

<decisions>
## Implementation Decisions

### CLI Command Structure
- Single command `xbm lan-cert` with `--status`, `--generate`, `--guide` flags — simpler discoverability, matches existing CLI flag pattern
- Explicit `--generate` flag required — prevents accidental certificate changes, clear intent
- Confirmation before overwrite with `--force` — prevents accidental data loss
- Manual CA installation (`mkcert -install`) with guidance — clearer separation of system-level vs app-level actions

### Certificate Storage & Detection
- Store certificates in `data/lan.crt` and `data/lan.key` — matches existing `data/localhost.*` pattern
- Use UDP socket trick (stdlib only) for LAN IP detection — `socket.connect(('8.8.8.8', 80))` gets primary outbound IP, zero new dependencies
- Check certificate expiration in `status` command, warn if < 30 days — proactive user awareness
- Backup old certificates (`lan.crt.bak`, `lan.key.bak`) before regeneration — safety net

### Platform Guidance
- Inline CLI output with `--guide` flag — immediate help, no external files needed
- Detect current OS and show relevant guide first, then "See other platforms: --guide --all" — focused output
- Print CA certificate path (`mkcert -CAROOT` output and `rootCA.pem` location) — helps user find file for mobile transfer
- Prominently highlight iOS extra step "Settings > General > About > Certificate Trust Settings" — commonly missed and breaks HTTPS

### Error Handling & Fallbacks
- Clear error with install instructions if mkcert not installed — guides user to fix immediately
- Warning message if CA installation fails, continue with certificate generation — user can run `mkcert -install` manually later
- Check for certs before `xbm web --lan` starts — fail with "Run `xbm lan-cert --generate` first" if missing
- Include IPv6 localhost (`::1`) in certificate SANs — future-proofs for IPv6 networks

### Claude's Discretion
Implementation details (exact output format, error message wording, table layout) are at Claude's discretion — use standard Rich library patterns and existing CLI command structure.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/web/certs.py` — existing self-signed certificate generation using `cryptography` library
- `src/config/settings.py` — Pydantic Settings pattern, add `lan_cert_path`, `lan_key_path`, `lan_enabled`
- `src/cli/main.py` — Typer CLI entry point, Rich console output, existing `web` command
- `src/web/app.py` — FastAPI app creation, uvicorn server startup

### Established Patterns
- CLI commands use Typer with Rich Console for output
- Settings use Pydantic BaseSettings with `.env` file support
- Certificate paths stored in `data/` directory, gitignored
- Error messages use Rich Panel with colored text and borders

### Integration Points
- `src/cli/main.py` — add `lan-cert` command group, modify `web` command with `--lan` flag
- `src/config/settings.py` — add LAN configuration settings
- `src/web/certs.py` — existing `ensure_https_certs()` for self-signed fallback
- New file: `src/web/lan_certs.py` — mkcert integration, LAN IP detection

</code_context>

<specifics>
## Specific Ideas

- Follow existing `xbm web` command structure with `--lan` flag
- Use Rich Panel with colored output for success/error messages (matches existing CLI style)
- Detect LAN IP at certificate generation time, not runtime (IP may change between networks)
- Show both localhost URL and LAN URL after certificate generation for clarity
- Platform detection via `platform.system()` (Darwin=macOS, Windows, Linux)

</specifics>

<deferred>
## Deferred Ideas

- **Auto-downloading mkcert:** User installs manually via package manager (less error-prone)
- **Automatic cert renewal:** Explicit `--generate --force` required for transparency
- **DNS hostname (e.g., mybookmarks.local):** Requires mDNS/Bonjour setup, defer to future milestone
- **psutil for all LAN IPs:** UDP socket trick sufficient for primary IP, defer multi-interface detection
- **Automatic CA installation:** Manual CA install with guidance provides better user control

</deferred>