# Phase 6: Web Foundation - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous workflow)

<domain>
## Phase Boundary

FastAPI web application that serves bookmarked posts via HTTP with shared CLI authentication. Users browse posts with pagination, search by text (FTS5), and filter by topic/author/date — all through a local web interface. This phase establishes the web foundation required for Google Cast integration (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Web Framework
- FastAPI + Jinja2 templates — lightweight, Python-native, async support for future scaling
- Uvicorn ASGI server — standard for FastAPI, supports HTTPS via ssl_context
- Server-side rendering (Jinja2) — simpler than SPA for CRUD interface, good for TV display

### Authentication Strategy
- Share CLI tokens directly from `data/tokens.json` — same user, same app credentials (WEB-03)
- No separate web auth — the web app is a local-only interface to the same data
- Session middleware optional — tokens are long-lived, can read per-request

### HTTPS Strategy (WEB-02)
- Self-signed certificate for localhost — required for Google Cast SDK
- Generate cert on first run or include pre-generated dev cert
- Certificate stored in `data/localhost.crt` and `data/localhost.key`

### Pagination
- Cursor-based pagination using `created_at` and `x_post_id` — stable ordering, no offset drift
- Default page size: 20 posts, configurable via query param
- "Load more" pattern for infinite scroll compatibility

### Search & Filter
- FTS5 full-text search already exists in `SearchService` — reuse for WEB-05
- Filter UI: topic dropdown, author search, date range picker
- Combine filters with AND logic, support multiple topic selection

### Claude's Discretion
- Template styling (minimal TV-friendly display)
- Exact API endpoint paths
- Error page design
- JavaScript framework for infinite scroll (vanilla JS vs HTMX vs Alpine)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/config/settings.py` — Pydantic Settings pattern, add `web_host`, `web_port`, `cert_path`
- `src/auth/oauth.py` — Token loading via `load_tokens()`, `ensure_authenticated()`
- `src/db/connection.py` — SQLite connection factory with WAL mode
- `src/repositories/posts.py` — PostsRepository with `get_all()`, `get_by_id()`
- `src/repositories/topics.py` — TopicsRepository for filter dropdown
- `src/services/search.py` — SearchService with FTS5, can be wrapped for web

### Established Patterns
- **Configuration:** Pydantic BaseSettings with `X_` env prefix, `.env` file support
- **Database:** Connection factory, context managers, repository pattern
- **CLI:** Typer app with Rich console output
- **Error handling:** `AuthError` class pattern, try/except with user-friendly messages

### Integration Points
- Web app reads same `data/tokens.json` as CLI
- Web app uses same `data/bookmarks.db` as CLI
- New web entry point: `src/web/__init__.py`, `src/web/app.py`, `src/web/routes/`
- Templates directory: `src/web/templates/` (Jinja2)
- Static files: `src/web/static/` (CSS, JS, images)

</code_context>

<specifics>
## Specific Ideas

- Home page shows recent posts with infinite scroll
- Search bar in header with real-time FTS5 search
- Filter panel: topic tags (click to filter), author (autocomplete), date range (calendar)
- Post card: author avatar, text preview, topics, date, link to original
- HTTPS certificate auto-generated on first `xbm web` run

</specifics>

<deferred>
## Deferred Ideas

- Google Cast integration — Phase 7
- Interactive review workflow (fresh/soon/later) — Phase 7 or later
- Topic management from web UI — deferred to v1.2
- Post editing/notes from web UI — out of scope for v1.1

</deferred>