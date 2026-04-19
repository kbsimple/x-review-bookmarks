# Phase 1: Foundation and Authentication - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can authenticate with X via OAuth 2.0 PKCE flow and the application has a working SQLite database with proper schema and WAL mode enabled.

This phase delivers:
- OAuth 2.0 PKCE authentication flow (initiate, authorize, exchange, store tokens)
- Secure token storage and refresh mechanism
- Graceful handling of expired/invalid tokens
- SQLite database initialization with users and tokens tables
- WAL mode enabled for concurrent read/write support

**Out of scope (Phase 2+):**
- Fetching bookmarks from X API
- Storing posts in the database
- Search functionality
- Topic organization
- Spaced repetition scheduling

</domain>

<decisions>
## Implementation Decisions

### Token Storage
- **D-01:** Token storage defaults to `data/tokens.json`, configurable via settings.
  - Rationale: Simple, consistent with x-api pattern, easy to debug.
  - Configurability allows users to override location if needed.

### Database Location
- **D-02:** SQLite database stored at `data/bookmarks.db`.
  - Rationale: Co-located with tokens for simplicity, consistent project structure.
  - Easy to find and backup; matches user expectation for CLI tool.

### Database Schema
- **D-03:** Phase 1 creates minimal schema: `users` and `tokens` tables only.
  - Posts table added in Phase 2 when needed.
  - Clean phase boundaries; schema grows with functionality.
  - Includes WAL mode and foreign key constraints as per requirements.

### OAuth Scopes
- **D-04:** OAuth scopes: `tweet.read`, `users.read`, `bookmark.read`, `offline.access`.
  - Minimal, purpose-specific permissions.
  - No unnecessary list permissions from x-api pattern.
  - `offline.access` required for refresh tokens.

### Claude's Discretion
- Token refresh logic — standard OAuth 2.0 flow, implement with tweepy.
- Error messages for auth failures — follow x-auth.py patterns.
- Database migration approach — simple initialization script, migrations deferred until needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authentication Pattern
- `../x-api/src/auth/x_auth.py` — Reference implementation for OAuth 2.0 PKCE flow, token persistence, callback server pattern

### Requirements
- `.planning/REQUIREMENTS.md` — AUTH-01, AUTH-02, AUTH-03, STOR-01, STOR-02
- `.planning/REQUIREMENTS.md` §Out of Scope — Thread context excluded, real-time sync excluded

### Research
- `.planning/research/SUMMARY.md` — Critical pitfalls section (403 Forbidden, 800 bookmark limit, rate limits, FK enforcement)
- `.planning/research/SUMMARY.md` §Recommended Stack — Python 3.10+, Typer, SQLite with WAL, pydantic-settings

### Architecture
- `CLAUDE.md` — Technology stack recommendations, SQLite configuration best practices

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **x-auth.py (x-api project):** Complete OAuth 2.0 PKCE implementation including:
  - `XAuth` dataclass for credential storage
  - `get_auth()` for loading credentials from environment
  - `verify_credentials()` for testing tokens
  - `get_authorization_url()` for PKCE flow initiation
  - `wait_for_callback()` for local callback server
  - `save_tokens()` / `load_tokens()` for persistence
  - `ensure_authenticated()` for first-run flow orchestration

### Established Patterns
- OAuth 2.0 PKCE with local callback server on port 8080
- Token persistence via JSON file
- Environment variables for client credentials (X_CLIENT_ID, X_CLIENT_SECRET)
- Error handling with AuthError exception class

### Integration Points
- New project will import/adapt patterns from x-auth.py
- SQLite initialization will be new (not in x-api)
- Database schema design is new for this project

</code_context>

<specifics>
## Specific Ideas

- Reuse x-auth.py patterns verbatim where possible to avoid re-implementing OAuth 2.0 PKCE (most common failure point per research)
- Use Typer for CLI entry point as recommended in stack
- Enable WAL mode and foreign key constraints on every connection (documented pitfall)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 01-foundation-and-authentication*
*Context gathered: 2026-04-18*