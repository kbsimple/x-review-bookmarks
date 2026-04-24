# Roadmap: X Bookmarked Posts Organizer

**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind

**Created:** 2026-04-18
**Granularity:** standard

## Overview

| Metric | Value |
|--------|-------|
| v1 Requirements | 34 |
| Phases | 5 |
| Milestone | Milestone 1 (CLI + SQLite) |

## Phases

- [x] **Phase 1: Foundation and Authentication** - OAuth 2.0 PKCE flow and SQLite database setup
- [x] **Phase 2: Bookmark Fetch and Storage** - X API integration for fetching and persisting bookmarks
- [x] **Phase 3: Search, Notes, and Import/Export** - Full-text search, personal notes, and data portability
- [ ] **Phase 4: Topic Organization** - Tags, topic taxonomy, and hybrid clustering
- [ ] **Phase 5: Spaced Repetition Resurfacing** - FSRS-based scheduling and review delivery

## Phase Details

### Phase 1: Foundation and Authentication
**Goal:** Users can authenticate with X and the application has a working SQLite database
**Depends on:** Nothing (first phase)
**Requirements:** AUTH-01, AUTH-02, AUTH-03, STOR-01, STOR-02
**Success Criteria** (what must be TRUE):
  1. User can initiate OAuth 2.0 PKCE flow and authorize the application with X
  2. Application stores access tokens securely and refreshes them when expired
  3. Application handles expired/invalid tokens gracefully with clear error messages
  4. SQLite database is initialized with proper schema and WAL mode enabled
**Plans:** 5 plans across 3 waves
Plans:
- [x] 01-00-PLAN.md — Test infrastructure (pytest config, test stubs)
- [x] 01-01-PLAN.md — Settings module (Pydantic configuration)
- [x] 01-02-PLAN.md — Database foundation (connection factory, schema)
- [x] 01-03-PLAN.md — OAuth implementation (PKCE flow, token persistence)
- [x] 01-04-PLAN.md — CLI entry point (auth and init commands)

### Phase 2: Bookmark Fetch and Storage
**Goal:** Users can sync their X bookmarks to local SQLite storage via CLI
**Depends on:** Phase 1
**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, STOR-03, CLI-01, CLI-05
**Success Criteria** (what must be TRUE):
  1. User can trigger a bookmark sync via CLI and see progress indication
  2. All bookmark content (text, author, images, links, media) is stored in SQLite
  3. Publication dates are stored for each post (required for scheduling)
  4. Sync handles rate limits gracefully and can resume from interruption
  5. Incremental sync only fetches new bookmarks (not full re-fetch every time)
**Plans:** 4 plans across 4 waves
Plans:
- [x] 02-01-PLAN.md — Test scaffolding and schema V2 (posts + sync_state tables)
- [x] 02-02-PLAN.md — XClient and repositories (API client, PostsRepository, SyncStateRepository)
- [x] 02-03-PLAN.md — SyncService (orchestration, incremental sync, rate limits)
- [x] 02-04-PLAN.md — CLI sync command (progress bar, summary table)

### Phase 3: Search, Notes, and Import/Export
**Goal:** Users can search stored posts, add notes, and export/import their data
**Depends on:** Phase 2
**Requirements:** SRCH-01, SRCH-02, SRCH-03, NOTE-01, NOTE-02, CLI-03, IMEX-01, IMEX-02, IMEX-03, MAINT-01, MAINT-02
**Success Criteria** (what must be TRUE):
  1. User can search posts by content (full-text search)
  2. User can search posts by author name or username
  3. User can add personal notes to any stored post
  4. User can export all stored posts to JSON or CSV format
  5. User can import posts from a JSON export
  6. User can identify posts with dead links
**Plans:** 6 plans across 4 waves
Plans:
- [x] 03-01-PLAN.md — Schema V3 and FTS5 (note column, link_status column, FTS5 virtual table, migrations)
- [x] 03-02-PLAN.md — SearchService (FTS5 full-text search, bm25 ranking, author filtering)
- [x] 03-03-PLAN.md — Export/Import Services (JSON/CSV export, JSON import, conflict resolution)
- [x] 03-04-PLAN.md — LinkCheckerService (async concurrent HTTP, semaphore limiting, caching)
- [x] 03-05-PLAN.md — CLI Commands: search and note
- [x] 03-06-PLAN.md — CLI Commands: export, import, check-links

### Phase 4: Topic Organization
**Goal:** Users can organize posts with tags and topics using a hybrid approach
**Depends on:** Phase 3
**Requirements:** ORG-01, ORG-02, ORG-03, ORG-04, CLI-04
**Success Criteria** (what must be TRUE):
  1. User can assign tags to bookmarked posts
  2. User can create and manage a predefined topic taxonomy
  3. Application suggests topic assignments using hybrid approach (predefined + AI-suggested)
  4. User can review and approve AI-suggested topic assignments
**Plans:** TBD

### Phase 5: Spaced Repetition Resurfacing
**Goal:** Posts are resurfaced for review on an exponential backoff schedule
**Depends on:** Phase 4
**Requirements:** SPAC-01, SPAC-02, SPAC-03, SPAC-04, CLI-02
**Success Criteria** (what must be TRUE):
  1. Application calculates next review date using exponential backoff from publication date
  2. User can view posts currently due for review via CLI
  3. User can trigger themed reviews (posts from specific topics)
  4. Notes attached to posts are displayed when post is resurfaced for review
**Plans:** TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Authentication | 5/5 | Complete | 2026-04-18 |
| 2. Bookmark Fetch and Storage | 4/4 | Complete | 2026-04-23 |
| 3. Search, Notes, and Import/Export | 6/6 | Complete | 2026-04-23 |
| 4. Topic Organization | 0/5 | Not started | - |
| 5. Spaced Repetition Resurfacing | 0/5 | Not started | - |

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| STOR-01 | Phase 1 | Complete |
| STOR-02 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 2 | Complete |
| DATA-05 | Phase 2 | Complete |
| STOR-03 | Phase 2 | Complete |
| CLI-01 | Phase 2 | Complete |
| CLI-05 | Phase 2 | Complete |
| SRCH-01 | Phase 3 | Complete |
| SRCH-02 | Phase 3 | Complete |
| SRCH-03 | Phase 3 | Complete |
| NOTE-01 | Phase 3 | Complete |
| NOTE-02 | Phase 3 | Complete |
| CLI-03 | Phase 3 | Complete |
| IMEX-01 | Phase 3 | Complete |
| IMEX-02 | Phase 3 | Complete |
| IMEX-03 | Phase 3 | Complete |
| MAINT-01 | Phase 3 | Complete |
| MAINT-02 | Phase 3 | Complete |
| ORG-01 | Phase 4 | Pending |
| ORG-02 | Phase 4 | Pending |
| ORG-03 | Phase 4 | Pending |
| ORG-04 | Phase 4 | Pending |
| CLI-04 | Phase 4 | Pending |
| SPAC-01 | Phase 5 | Pending |
| SPAC-02 | Phase 5 | Pending |
| SPAC-03 | Phase 5 | Pending |
| SPAC-04 | Phase 5 | Pending |
| CLI-02 | Phase 5 | Pending |

---
*Roadmap created: 2026-04-18*
*Roadmap updated: 2026-04-23 - Phase 2 and 3 complete*
