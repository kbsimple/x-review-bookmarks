# Project Research Summary

**Project:** X Bookmarked Posts Organizer — Web App with Casting (v1.1)
**Domain:** FastAPI web application with Google Cast integration
**Researched:** 2026-05-17
**Confidence:** HIGH

## Executive Summary

Milestone v1.1 adds a FastAPI web frontend with Google Cast integration to the existing CLI application. Research recommends FastAPI 0.136+ with Jinja2 templates for server-side rendering, aiosqlite for async database operations, and the Google Cast Web Sender SDK for TV display. The web app shares OAuth tokens and SQLite database with the existing CLI, avoiding duplication.

Key risks: SQLite thread safety (mitigated by WAL mode and per-request connections), HTTPS requirement for Cast SDK (mitigated by mkcert for development), and Default Media Receiver limitations for text content (requires custom Web Receiver).

## Key Findings

### Recommended Stack

**New additions for v1.1:**
- **FastAPI 0.136+** — Web framework with native Jinja2Templates support
- **aiosqlite 0.20+** — Async SQLite driver (sync sqlite3 blocks event loop)
- **Jinja2 3.1.6** — HTML templating
- **python-multipart 0.0.28** — Form data parsing
- **mkcert** — Local HTTPS certificates (required for Cast SDK)
- **Web Sender SDK** — JavaScript SDK for Cast button

### Expected Features

**Must have (table stakes):**
- Cast button with connection states
- Session management (connect/disconnect)
- Mini controller during active cast
- HTTPS secure context
- Post browsing with cursor pagination
- Search/filter extending FTS5

**Should have (differentiators):**
- Custom Web Receiver for text/image content
- Media Browse landing page on TV
- Shared authentication with CLI

**Defer (v2+):**
- Touch-optimized receiver UI
- Voice commands
- Reading position persistence

### Architecture Approach

FastAPI as parallel module to CLI (`src/web/` alongside `src/cli/`), sharing service and repository layers. OAuth tokens in `data/tokens.json` shared between CLI and web. Per-request DB connections with WAL mode.

**Major components:**
1. `src/web/app.py` — FastAPI application factory
2. `src/web/routes/web.py` — HTML routes
3. `src/web/routes/api.py` — JSON API
4. `src/web/static/js/cast.js` — Cast sender integration
5. `src/web/auth.py` — Session auth with token sharing

### Critical Pitfalls

1. **SQLite thread safety** — Use `check_same_thread=False` and per-request connections
2. **HTTPS required for Cast** — Self-signed certs rejected; use mkcert
3. **Never store tokens in localStorage** — XSS vulnerability; read server-side
4. **Event loop blocking** — Use async drivers or sync `def` routes
5. **Custom Web Receiver needed** — Default Media Receiver is video-focused

## Implications for Roadmap

### Phase 6: Web Foundation
**Rationale:** HTTPS and database connectivity are prerequisites.
**Delivers:** FastAPI app, HTTPS, shared auth, post browsing, search/filter
**Addresses:** Table stakes (HTTPS, browsing, search), pitfalls (thread safety, auth)

### Phase 7: Cast Integration
**Rationale:** Requires secure context from Phase 6.
**Delivers:** Cast button, session management, Custom Web Receiver, mini controller
**Addresses:** Differentiators (Cast, custom receiver)

### Phase 8: Enhanced Features (Optional)
**Rationale:** Polish after core validates.
**Delivers:** Reading position persistence, touch UI, topic collections on TV

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official FastAPI, Jinja2, Google Cast docs verified |
| Features | HIGH | Google Cast Design Checklist official |
| Architecture | HIGH | Existing codebase analyzed, patterns established |
| Pitfalls | HIGH | Multiple sources for each pitfall |

**Overall confidence:** HIGH

## Sources

### Primary (HIGH confidence)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cast Web Sender Integration](https://developers.google.com/cast/docs/web_sender/integrate)
- [Google Cast Design Checklist](https://developers.google.com/cast/docs/design_checklist)

### Secondary (MEDIUM confidence)
- [FastAPI Project Structure Guide 2026](https://dev.to/thesius_code_7a136ae718b7/production-ready-fastapi-project-structure-2026-guide-b1g)
- [OAuth Token Sharing Patterns](https://kharkevich.org/2024/11/30/oidc-cli-auth/)

---
*Research completed: 2026-05-17*
*Ready for roadmap: yes*