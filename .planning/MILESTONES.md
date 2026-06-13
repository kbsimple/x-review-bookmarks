# Milestone History

## Milestone 1 (v1.0): CLI + SQLite

**Status:** Complete
**Started:** 2026-04-18
**Completed:** 2026-04-25

**Goal:** Build core CLI functionality for fetching, storing, and organizing bookmarked posts.

**Delivered:**
- OAuth 2.0 PKCE authentication with X API
- SQLite storage with WAL mode (posts, tags, topics, review state)
- Bookmark sync with incremental updates and rate limit handling
- FTS5 full-text search across post content and authors
- Personal notes attached to posts
- JSON/CSV export and import
- Tags and topic taxonomy with hybrid AI suggestions
- FSRS-based spaced repetition scheduling
- Interactive review sessions via CLI

**Phases:** 5
**Requirements:** 34
**Plans:** 22

---

## Milestone 2 (v1.1): Web + Cast

*(Archive not yet created — see ROADMAP.md Phase 6–7 for details)*

---

## Milestone 3 (v1.2): Embedded Posts Display

*(Archive not yet created — see ROADMAP.md Phase 8–11 for details)*

---

## Milestone 4 (v1.3): LAN Casting Support

*(Archive not yet created — see ROADMAP.md Phase 12–13 for details)*

---

## Milestone 5 (v1.4): Static Export

**Status:** Complete
**Started:** 2026-06-13
**Completed:** 2026-06-13

**Goal:** Export bookmarks to a static web app deployable on Netlify — browse, search, and filter bookmarks from any browser without running the local server.

**Delivered:**
- `xbm export-static` CLI command with --output and --db flags
- StaticExportService generating 7 files (5 JSON data files + index.html + netlify.toml)
- Self-contained index.html viewer: dark theme, sticky header, client-side search (Array.filter), date filtering (7 shortcuts), sort by newest/oldest/author
- All user content HTML-escaped via esc() helper (XSS prevention)
- netlify.toml with Cache-Control headers for Netlify CDN
- Repository extensions: PostsRepository.get_all_with_embedded(), ReviewStateRepository.get_all()
- 31 new tests (27 service tests + 4 CLI integration tests)

**Phases:** 1 (Phase 14: Static Export)
**Plans:** 5 (Wave 0–4)

---
*Last updated: 2026-06-13*