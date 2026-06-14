# Phase 2: Bookmark Fetch and Storage - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can sync their X bookmarks to local SQLite storage via CLI, with full content storage (text, author, images, links, media), publication dates for scheduling, rate limit handling, and incremental sync support.

This phase delivers:
- CLI `sync` command to fetch bookmarks from X API
- Posts table schema with full content storage
- Rate limit handling with auto-wait and pagination state
- Incremental sync (only fetch new bookmarks)
- Rich output with progress indication and summary

**Out of scope (Phase 3+):**
- Full-text search within stored posts
- Topic clustering and assignment
- Spaced repetition scheduling
- Import/export functionality
- Notes on bookmarks

</domain>

<decisions>
## Implementation Decisions

### Posts Table Schema
- **D-01:** Posts table stores full bookmark content including:
  - Post metadata: `x_post_id` (primary key), `created_at` (publication date)
  - Content: `text`, `author_id`, `author_username`, `author_display_name`
  - Media: `media_urls` (JSON array), `link_urls` (JSON array)
  - Bookmark metadata: `bookmarked_at` (when user bookmarked it)
  - Sync metadata: `fetched_at`, `sync_version`
  - Rationale: DATA-02, DATA-03 require full content and publication dates. X API has 800 bookmark limit so rich schema is acceptable.

### Incremental Sync Strategy
- **D-02:** Incremental sync via bookmark ID comparison.
  - Store `last_sync_bookmark_id` and `last_sync_at` in sync_state table
  - Fetch only bookmarks newer than last sync
  - Fallback to full sync if no sync history exists
  - Rationale: STOR-03 requires incremental sync. ID comparison is more reliable than timestamp (clock skew issues).

### Rate Limit Handling
- **D-03:** Auto-wait with progress indication.
  - Display countdown when approaching rate limit
  - Auto-resume when 15-minute window resets
  - Persist pagination `next_token` to database for resume after interruption
  - Rationale: DATA-04 requires graceful rate limit handling. Auto-wait provides better UX than failing.

### Sync Command Output
- **D-04:** Progress bar during sync + Rich summary table after.
  - Live progress bar showing fetch progress
  - Summary table with counts: total, new, updated, errors
  - Sample of newly fetched posts with author and content preview
  - Rationale: CLI-05 requires rich output with post content and metadata.

### API Client Architecture
- **D-05:** Dedicated `api/x_client.py` module.
  - Wrapper around tweepy.Client for X API v2 calls
  - Encapsulates rate limiting logic, pagination state management
  - Returns typed data structures (dataclasses or Pydantic models)
  - Rationale: Research recommends this pattern for clean separation of concerns.

### Claude's Discretion
- Exact column types and constraints (TEXT vs JSON for media arrays)
- Error message wording for sync failures
- Progress bar styling (Rich Progress component choice)
- Pagination batch size (balance between speed and rate limit conservation)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authentication Pattern (from Phase 1)
- `src/auth/oauth.py` — OAuth 2.0 PKCE implementation, ensure_authenticated(), XAuth dataclass
- `src/auth/__init__.py` — Module exports

### Database Pattern (from Phase 1)
- `src/db/connection.py` — get_connection() with WAL mode and FK constraints
- `src/db/schema.py` — SCHEMA_V1 pattern, posts table to be added

### CLI Pattern (from Phase 1)
- `src/cli/main.py` — Typer app structure, Rich console usage, command patterns

### Configuration (from Phase 1)
- `src/config/settings.py` — Settings class with Pydantic

### Research
- `.planning/research/SUMMARY.md` — Critical pitfalls (403 Forbidden, 800 bookmark limit, rate limits)
- `.planning/research/SUMMARY.md` §Phase 2 — "Tweepy usage is standard, repository pattern is well-established"

### Requirements
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-05, STOR-03, CLI-01, CLI-05

### External Reference
- `../x-api/src/auth/x_auth.py` — Reference implementation patterns (if needed)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **src/auth/oauth.py:** `ensure_authenticated()` returns XAuth with access_token for API calls
- **src/db/connection.py:** `get_connection()` provides WAL-enabled SQLite connection
- **src/db/schema.py:** Pattern for schema SQL, posts table will extend this
- **src/cli/main.py:** Typer app instance, Rich console, command decorator patterns
- **src/config/settings.py:** Settings class with database_path, token_path

### Established Patterns
- OAuth 2.0 PKCE flow complete and working
- SQLite with WAL mode and FK constraints on every connection
- Typer CLI with Rich formatting for output
- Settings via Pydantic with environment variables (X_CLIENT_ID, X_CLIENT_SECRET)

### Integration Points
- New `api/` module for X API client (to be created)
- New `services/` or `repositories/` module for business logic (to be created)
- Posts table schema added to `src/db/schema.py`
- New `sync` command in `src/cli/main.py`
- Database path from Settings already configured

</code_context>

<specifics>
## Specific Ideas

- Follow tweepy patterns from research: use `tweepy.Client(bearer_token=access_token)` for user-context calls
- Store pagination `next_token` in database to enable resume after interruption (DATA-04)
- Display clear warning about 800 bookmark limit if user approaches it (DATA-05)
- Progress bar should show both "fetched X/Y" and "rate limit remaining: N requests"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 02-bookmark-fetch-and-storage*
*Context gathered: 2026-04-19*