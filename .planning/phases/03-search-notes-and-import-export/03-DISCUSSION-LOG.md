# Phase 3: Search, Notes, and Import/Export - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 03-search-notes-and-import-export
**Areas discussed:** Search implementation, Notes storage, Export/Import format, Dead link detection

---

## Search Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite FTS5 | Virtual table for full-text search with ranking, phrase search, and highlights. Integrates cleanly with PostsRepository. | ✓ |
| LIKE queries | Simple pattern matching for text/author. Works for small datasets but no ranking or phrase support. | |
| Whoosh library | Python search library with stemming and fuzzy matching. More features but extra dependency and index management. | |

**User's choice:** SQLite FTS5 (recommended)
**Notes:** Built into SQLite, handles 100-500 records easily, supports ranking and highlighting without external dependencies.

---

## Notes Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Column in posts | Add `note TEXT` column to posts table. Notes always available when fetching posts. Simple for 100-500 record scale. | ✓ |
| Separate notes table | Create `notes` table with post_id foreign key. Notes fetched separately. More normalized but adds JOIN overhead for every display. | |

**User's choice:** Column in posts (recommended)
**Notes:** Simple for the scale, notes always available when fetching posts, avoids JOIN overhead. Phase 5's spaced repetition will need notes alongside posts.

---

## Export/Import Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON + CSV | JSON with metadata wrapper (version, timestamp, source) + posts array. CSV exports core fields only (text, author, date, note). JSON for complete data portability. | ✓ |
| Full JSON and CSV | JSON array only, no wrapper. CSV exports all fields with JSON-encoded arrays for media/links. Maximum completeness but harder to parse. | |

**User's choice:** JSON + CSV (recommended)
**Notes:** JSON provides complete portability with metadata for future format changes; CSV is spreadsheet-friendly with essential data. Import supports JSON format only.

---

## Dead Link Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Async concurrent | Use httpx or aiohttp for concurrent HTTP HEAD requests. Check up to 10 links at a time, cache results in posts table. Rich progress bar during check. | ✓ |
| Synchronous HTTP HEAD | Simple HTTP HEAD requests one at a time. Works but slow for many links. Blocks CLI during check. | |
| Lazy check on demand | Only check links when viewing a post. No upfront cost, but may miss dead links until user views them. | |

**User's choice:** Async concurrent (recommended)
**Notes:** Non-blocking for CLI UX, concurrent checks handle many links efficiently, caching prevents redundant network requests.

---

## Claude's Discretion

- Exact FTS5 query syntax and ranking function
- Error messages for failed searches/exports
- Progress bar styling for link checks
- Import conflict resolution (skip existing vs update)

## Deferred Ideas

None — discussion stayed within phase scope.