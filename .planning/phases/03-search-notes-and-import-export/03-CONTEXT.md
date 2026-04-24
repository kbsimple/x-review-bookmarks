# Phase 3: Search, Notes, and Import/Export - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can search stored posts by content and author, add personal notes to posts, export/import data, and identify posts with dead links.

This phase delivers:
- Full-text search within stored post content (SRCH-01)
- Search by author name or username (SRCH-02)
- Search results with relevant context (SRCH-03)
- Personal notes attached to posts (NOTE-01, NOTE-02)
- JSON export with metadata wrapper (IMEX-01)
- CSV export with core fields (IMEX-02)
- JSON import for data portability (IMEX-03)
- Dead link detection and filtering (MAINT-01, MAINT-02)
- CLI commands: `search`, `note`, `export`, `import`, `check-links`

**Out of scope (Phase 4+):**
- Topic clustering and assignment
- Tags and taxonomy management
- Spaced repetition scheduling
- Samsung TV viewing interface

</domain>

<decisions>
## Implementation Decisions

### Search Implementation
- **D-01:** SQLite FTS5 virtual table for full-text search.
  - Create `posts_fts` virtual table using FTS5 with `posts` as content table
  - Support phrase search (`"exact phrase"`), ranking by relevance, and snippet highlighting
  - Integrate with PostsRepository via new `search()` method
  - Rationale: Built into SQLite, handles 100-500 records easily, supports ranking and highlighting without external dependencies.

### Notes Storage
- **D-02:** Add `note TEXT` column to posts table.
  - Single column for personal notes attached to each post
  - NULL for posts without notes
  - Notes displayed in Phase 5's spaced repetition review
  - Rationale: Simple for the scale, notes always available when fetching posts, avoids JOIN overhead.

### Export/Import Format
- **D-03:** JSON with metadata wrapper for export, CSV with core fields.
  - JSON format: `{version: "1.0", exported_at: ISO_DATE, source: "xbm", posts: [...]}`
  - CSV format: Core fields only (id, text, author_username, created_at, note)
  - Media/link arrays omitted from CSV (use JSON for complete data)
  - Import supports JSON format only
  - Rationale: JSON provides complete portability with metadata; CSV is spreadsheet-friendly with essential data.

### Dead Link Detection
- **D-04:** Async concurrent HTTP HEAD requests with caching.
  - Use `httpx` or `aiohttp` for concurrent checks (max 10 concurrent)
  - Store link status in posts table (`link_status TEXT` column: "ok", "dead", "unchecked", or ISO timestamp of last check)
  - Rich progress bar during check via Typer + Rich
  - Cache results to avoid re-checking on subsequent runs
  - Rationale: Non-blocking for CLI UX, concurrent checks handle many links efficiently, caching prevents redundant network requests.

### CLI Commands
- **D-05:** Command structure follows established Typer pattern.
  - `xbm search <query>` — Full-text and author search with results display
  - `xbm note <post_id> [text]` — Add/update/remove note on a post
  - `xbm export [--format json|csv] [--output file]` — Export all posts
  - `xbm import <file>` — Import posts from JSON export
  - `xbm check-links [--fix]` — Check links and optionally filter dead ones
  - Rationale: Consistent with existing `xbm sync` command pattern.

### Claude's Discretion
- Exact FTS5 query syntax and ranking function
- Error messages for failed searches/exports
- Progress bar styling for link checks
- Import conflict resolution (skip existing vs update)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Authentication Pattern (from Phase 1)
- `src/auth/oauth.py` — OAuth 2.0 PKCE implementation, ensure_authenticated(), XAuth dataclass

### Database Pattern (from Phase 1 & 2)
- `src/db/connection.py` — get_connection() with WAL mode and FK constraints
- `src/db/schema.py` — SCHEMA_V2 with posts table, sync_state table
- `src/repositories/posts.py` — PostsRepository pattern for database access

### CLI Pattern (from Phase 1 & 2)
- `src/cli/main.py` — Typer app structure, Rich console usage, command patterns

### Services Pattern (from Phase 2)
- `src/services/sync.py` — SyncService orchestration pattern

### Requirements
- `.planning/REQUIREMENTS.md` — SRCH-01, SRCH-02, SRCH-03, NOTE-01, NOTE-02, CLI-03, IMEX-01, IMEX-02, IMEX-03, MAINT-01, MAINT-02

### Prior Phase Context
- `.planning/phases/02-bookmark-fetch-and-storage/02-CONTEXT.md` — PostsRepository established, sync pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **src/repositories/posts.py:** PostsRepository with upsert, get_by_id, get_all, count — extend with search(), add_note()
- **src/services/sync.py:** Async service pattern — similar pattern for link checking
- **src/cli/main.py:** Typer CLI with Rich — add search, note, export, import, check-links commands
- **src/db/schema.py:** Schema management — add FTS5 virtual table, note column, link_status column

### Established Patterns
- SQLite with WAL mode and FK constraints on every connection
- Repository pattern for database access (PostsRepository, SyncStateRepository)
- Typer CLI with Rich formatting for output
- Async service orchestration with callbacks (from SyncService)

### Integration Points
- Add `posts_fts` FTS5 virtual table to schema
- Add `note` and `link_status` columns to posts table
- Create `src/services/search.py` for FTS5 query logic
- Create `src/services/export.py` for JSON/CSV export
- Create `src/services/link_checker.py` for async link checking
- Add `search`, `note`, `export`, `import`, `check-links` commands to CLI

</code_context>

<specifics>
## Specific Ideas

- FTS5 should index text and author_username for combined search
- JSON export should include version field for future format changes
- Link status check should batch (e.g., check 10 links concurrently)
- Note command: `xbm note <post_id>` shows current note, `xbm note <post_id> "text"` adds/updates, `xbm note <post_id> --clear` removes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 03-search-notes-and-import-export*
*Context gathered: 2026-04-23*