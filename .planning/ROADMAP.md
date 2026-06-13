# Roadmap: X Bookmarked Posts Organizer

**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind

**Created:** 2026-04-18
**Granularity:** standard

## Overview

| Metric | Value |
|--------|-------|
| v1.0 Requirements | 34 (Complete) |
| v1.1 Requirements | 14 (Complete) |
| v1.2 Requirements | 13 (Complete) |
| v1.3 Requirements | 14 (Planned) |
| Phases | 13 |
| Milestone | Milestone 4 (v1.3 — LAN Casting Support) |

## Phases

- [x] **Phase 1: Foundation and Authentication** - OAuth 2.0 PKCE flow and SQLite database setup
- [x] **Phase 2: Bookmark Fetch and Storage** - X API integration for fetching and persisting bookmarks
- [x] **Phase 3: Search, Notes, and Import/Export** - Full-text search, personal notes, and data portability
- [x] **Phase 4: Topic Organization** - Tags, topic taxonomy, and hybrid clustering
- [x] **Phase 5: Spaced Repetition Resurfacing** - FSRS-based scheduling and review delivery
- [x] **Phase 6: Web Foundation** - FastAPI web app with shared authentication and post browsing
- [x] **Phase 7: Cast Integration** - Google Cast integration for TV viewing
- [x] **Phase 8: Storage Foundation** - Fetch and store embedded post data with proper schema and X API expansions
- [x] **Phase 9: Web Display** - Render retweets and quote tweets in web interface with nested layouts
- [x] **Phase 10: CLI Display** - Render embedded posts in terminal with Rich Panel/Tree components
- [x] **Phase 11: Cast Display** - Display embedded posts on TV with TV-optimized visual styling
- [x] **Phase 12: Certificate Management** - LAN SSL certificate generation and CLI commands
- [x] **Phase 13: LAN Network Access** - Web server LAN binding and mobile device access
- [ ] **Phase 14: Static Export** - Export bookmarks to static JSON for cloud hosting

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
- [x] 03-02-PLAN.md — SearchService (FTS5 full-text search, bm26 ranking, author filtering)
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
**Plans:** 6 plans across 4 waves
Plans:
- [x] 04-00-PLAN.md — Test infrastructure and dependencies
- [x] 04-01-PLAN.md — Schema V4 and TagsRepository
- [x] 04-02-PLAN.md — TopicsRepository with pending assignment workflow
- [x] 04-03-PLAN.md — EmbeddingService and ClusteringService
- [x] 04-04-PLAN.md — TopicSuggesterService for hybrid suggestions
- [x] 04-05-PLAN.md — CLI commands: tag, topic, suggest-topics, review-topics

### Phase 5: Spaced Repetition Resurfacing
**Goal:** Posts are resurfaced for review on a user-controlled schedule with hybrid algorithm support
**Depends on:** Phase 4
**Requirements:** SPAC-01, SPAC-02, SPAC-03, SPAC-04, CLI-02
**Success Criteria** (what must be TRUE):
  1. Application calculates next review date from publication date with FSRS state tracking
  2. User can view currently due posts via CLI (`xbm due`)
  3. User can trigger themed reviews via `--topic` flag
  4. Notes attached to posts are displayed prominently during review
  5. User chooses scheduling intent (fresh/soon/later) with defined intervals
**Plans:** 4 plans across 4 waves
Plans:
- [x] 05-01-PLAN.md — Schema V5 and ReviewStateRepository (post_review_state table, CRUD operations)
- [x] 05-02-PLAN.md — ReviewScheduler service (FSRS Card state, user intervals)
- [x] 05-03-PLAN.md — CLI commands: due, review (interactive session, themed reviews)
- [x] 05-04-PLAN.md — CLI commands: stats, reset, seed (progress tracking, state management)

### Phase 6: Web Foundation
**Goal:** Users can browse and search posts via a local web application with shared CLI authentication
**Depends on:** Phase 5
**Requirements:** WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06
**Success Criteria** (what must be TRUE):
  1. User can access the application via web browser at localhost
  2. Web app serves content over HTTPS (required for Google Cast)
  3. Web app authenticates using shared CLI tokens (data/tokens.json)
  4. User can browse posts with cursor-based pagination
  5. User can search posts by text content (FTS5)
  6. User can filter posts by topic, author, and date range
**Plans:** 4 plans across 4 waves
Plans:
- [x] 06-01-PLAN.md — FastAPI foundation (app structure, HTTPS server, Jinja2 templates)
- [x] 06-02-PLAN.md — Web authentication (shared token loader, session middleware)
- [x] 06-03-PLAN.md — Post browsing (pagination endpoints, post card components)
- [x] 06-04-PLAN.md — Search and filter (FTS5 integration, filter UI, result rendering)

### Phase 7: Cast Integration
**Goal:** Users can cast posts to Chromecast/Smart TV devices for viewing on the big screen
**Depends on:** Phase 6
**Requirements:** CAST-01, CAST-02, CAST-03, CAST-04, CAST-05, RCVR-01, RCVR-02, RCVR-03
**Success Criteria** (what must be TRUE):
  1. User sees Cast button in web app header when devices are available
  2. User can connect to Chromecast/Smart TV devices from web app
  3. User can cast post content to TV screen
  4. Mini controller displays during active cast session with navigation controls
  5. Cast session state persists across navigation in the web app
  6. Custom Web Receiver displays post text and images on TV
  7. Receiver handles post content loading from web app
  8. Receiver displays post author and publication date
**Plans:** 4 plans across 4 waves
Plans:
- [x] 07-01-PLAN.md — Google Cast SDK integration (Cast button, device discovery, session management)
- [x] 07-02-PLAN.md — Custom Web Receiver (Styled Media Receiver, post display layout)
- [x] 07-03-PLAN.md — Cast messaging (post data transfer, receiver message handling)
- [x] 07-04-PLAN.md — Mini controller (persistent controls, navigation, queue management)

### Phase 8: Storage Foundation
**Goal:** Users' synced bookmarks include embedded post data for retweets and quote tweets
**Depends on:** Phase 7
**Requirements:** STR-01, STR-02, STR-03
**Success Criteria** (what must be TRUE):
  1. User can sync bookmarks and embedded posts are stored in database
  2. Each post has a type indicating whether it is original, retweet, or quote
  3. Embedded posts have an available flag that indicates deleted/protected originals
  4. Original post content (text, author, media) is queryable from embedded_posts table
Plans:
- [x] 08-00-PLAN.md — Test scaffolding (migration tests, repository tests, sync tests)
- [x] 08-01-PLAN.md — Schema migration V6 and XClient expansions
- [x] 08-02-PLAN.md — EmbeddedPostsRepository creation
- [ ] 08-03-PLAN.md — SyncService integration

### Phase 9: Web Display
**Goal:** Users can view retweets and quote tweets with full original content in the web interface
**Depends on:** Phase 8
**Requirements:** WEB-07, WEB-08, WEB-09, WEB-10
**Success Criteria** (what must be TRUE):
  1. User sees quote tweets with their commentary above the nested original post
  2. User sees retweets with original author attribution and content
  3. User sees images and videos from embedded posts inline
  4. User sees "Original post unavailable" placeholder when embedded post is deleted/protected
Plans:
- [x] 09-00-PLAN.md — Test scaffolding for embedded post rendering
- [x] 09-01-PLAN.md — Repository LEFT JOIN for embedded posts
- [x] 09-02-PLAN.md — Template macros for conditional post cards
- [x] 09-03-PLAN.md — HTMX endpoint and end-to-end tests
**UI hint:** yes

### Phase 10: CLI Display
**Goal:** Users can view embedded posts with clear visual hierarchy in terminal output
**Depends on:** Phase 8
**Requirements:** CLI-06, CLI-07, CLI-08
**Success Criteria** (what must be TRUE):
  1. User sees quote tweets rendered with Rich Panel showing nested structure
  2. User sees retweets with "Reposted from @username" indicator and original content
  3. User sees media URLs from embedded posts in CLI output
Plans:
- [x] 10-00-PLAN.md — Test scaffolding for CLI embedded post rendering
- [x] 10-01-PLAN.md — CLI output formatting for retweets
- [x] 10-02-PLAN.md — CLI output formatting for quote tweets

### Phase 11: Cast Display
**Goal:** Users can view embedded posts on TV with readable layout and visual separation
**Depends on:** Phase 8
**Requirements:** CAST-06, CAST-07, CAST-08
**Success Criteria** (what must be TRUE):
  1. User sees embedded posts on TV with larger text sizes and nested cards
  2. User sees embedded content with distinct background colors and clear borders
  3. User sees "Original post unavailable" message when embedded post is deleted
Plans:
- [x] 11-00-PLAN.md — Test scaffolding for cast embedded post rendering
- [x] 11-01-PLAN.md — Cast receiver embedded post layout
- [x] 11-02-PLAN.md — Cast messaging for embedded posts
**UI hint:** yes

### Phase 12: Certificate Management
**Goal:** Users can check, generate, and manage LAN SSL certificates via CLI
**Depends on:** Phase 11
**Requirements:** CERT-01, CERT-02, CERT-03, CERT-04, MAINT-01, MAINT-02
**Success Criteria** (what must be TRUE):
  1. User runs `xbm lan-cert status` and sees mkcert installation status, CA location, and certificate status
  2. User runs `xbm lan-cert generate` and certificates are created for localhost and LAN IP
  3. User sees clear guidance on how to install CA certificate on mobile devices
  4. System detects primary LAN IP automatically during certificate generation
  5. User can regenerate certificates when expired or LAN IP changes
**Plans:** 3 plans across 2 waves
Plans:
- [ ] 12-01-PLAN.md — Certificate utilities (lan_certs.py, LAN IP detection, settings)
- [ ] 12-02-PLAN.md — CLI status and generate commands (lan-cert --status, --generate)
- [ ] 12-03-PLAN.md — CLI guide command (lan-cert --guide, platform instructions)

### Phase 13: LAN Network Access
**Goal:** Users can access the web app from mobile devices on the same LAN without certificate warnings
**Depends on:** Phase 12
**Requirements:** NET-01, NET-02, NET-03
**Success Criteria** (what must be TRUE):
  1. User runs `xbm web --lan` and server binds to all network interfaces (0.0.0.0)
  2. User sees both localhost URL and LAN URL displayed in console after server startup
  3. Mobile browser can access web app via HTTPS without certificate warnings (after CA installation from Phase 12)
Plans: 1 plan in 1 wave
Plans:
- [ ] 13-01-PLAN.md — LAN network access (--lan flag, certificate check, dual URL display)

### Phase 14: Static Export
**Goal:** Users can export their bookmarks to static JSON files and deploy to free static hosting (Netlify/Cloudflare Pages)
**Depends on:** Phase 13
**Requirements:** EXPORT-01, EXPORT-02, EXPORT-03, EXPORT-04
**Success Criteria** (what must be TRUE):
  1. User runs `xbm export-static` and generates JSON files for all posts, tags, topics, and review state
  2. User can deploy exported files to Netlify or Cloudflare Pages for free hosting
  3. Static web app displays posts with search functionality (client-side)
  4. Export includes pre-built search index for instant client-side search
**Plans:** 5 plans across 5 waves
Plans:
- [x] 14-00-PLAN.md — Test infrastructure (conftest temp_db_v6 fixture, stub test files)
- [x] 14-01-PLAN.md — Repository extensions (PostsRepository.get_all_with_embedded, ReviewStateRepository.get_all)
- [x] 14-02-PLAN.md — StaticExportService JSON writers (5 JSON files)
- [x] 14-03-PLAN.md — index.html and netlify.toml generation (complete service)
- [ ] 14-04-PLAN.md — CLI command export-static (progress bar, summary table, deployment instructions)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Authentication | 5/5 | Complete | 2026-04-18 |
| 2. Bookmark Fetch and Storage | 4/4 | Complete | 2026-04-23 |
| 3. Search, Notes, and Import/Export | 6/6 | Complete | 2026-04-23 |
| 4. Topic Organization | 6/6 | Complete | 2026-04-25 |
| 5. Spaced Repetition Resurfacing | 4/4 | Complete | 2026-04-25 |
| 6. Web Foundation | 4/4 | Complete | 2026-05-17 |
| 7. Cast Integration | 4/4 | Complete | 2026-05-17 |
| 8. Storage Foundation | 3/4 | Complete | 2026-06-04 |
| 9. Web Display | 4/4 | Complete | 2026-06-06 |
| 10. CLI Display | 3/3 | Complete | 2026-06-07 |
| 11. Cast Display | 3/3 | Complete | 2026-06-07 |
| 12. Certificate Management | 3/3 | Complete | 2026-06-08 |
| 13. LAN Network Access | 1/1 | Complete | 2026-06-08 |
| 14. Static Export | 4/5 | In progress | - |

## Coverage

### v1.0 Requirements (Complete)

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
| ORG-01 | Phase 4 | Complete |
| ORG-02 | Phase 4 | Complete |
| ORG-03 | Phase 4 | Complete |
| ORG-04 | Phase 4 | Complete |
| CLI-04 | Phase 4 | Complete |
| SPAC-01 | Phase 5 | Complete |
| SPAC-02 | Phase 5 | Complete |
| SPAC-03 | Phase 5 | Complete |
| SPAC-04 | Phase 5 | Complete |
| CLI-02 | Phase 5 | Complete |

### v1.1 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| WEB-01 | Phase 6 | Complete |
| WEB-02 | Phase 6 | Complete |
| WEB-03 | Phase 6 | Complete |
| WEB-04 | Phase 6 | Complete |
| WEB-05 | Phase 6 | Complete |
| WEB-06 | Phase 6 | Complete |
| CAST-01 | Phase 7 | Complete |
| CAST-02 | Phase 7 | Complete |
| CAST-03 | Phase 7 | Complete |
| CAST-04 | Phase 7 | Complete |
| CAST-05 | Phase 7 | Complete |
| RCVR-01 | Phase 7 | Complete |
| RCVR-02 | Phase 7 | Complete |
| RCVR-03 | Phase 7 | Complete |

### v1.2 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| STR-01 | Phase 8 | Complete |
| STR-02 | Phase 8 | Complete |
| STR-03 | Phase 8 | Complete |
| WEB-07 | Phase 9 | Complete |
| WEB-08 | Phase 9 | Complete |
| WEB-09 | Phase 9 | Complete |
| WEB-10 | Phase 9 | Complete |
| CLI-06 | Phase 10 | Complete |
| CLI-07 | Phase 10 | Complete |
| CLI-08 | Phase 10 | Complete |
| CAST-06 | Phase 11 | Complete |
| CAST-07 | Phase 11 | Complete |
| CAST-08 | Phase 11 | Complete |

### v1.3 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| CERT-01 | Phase 12 | Complete |
| CERT-02 | Phase 12 | Complete |
| CERT-03 | Phase 12 | Complete |
| CERT-04 | Phase 12 | Complete |
| MAINT-01 | Phase 12 | Complete |
| MAINT-02 | Phase 12 | Complete |
| NET-01 | Phase 13 | Complete |
| NET-02 | Phase 13 | Complete |
| NET-03 | Phase 13 | Complete |
| PLAT-01 | Phase 13 | Complete |
| PLAT-02 | Phase 13 | Complete |
| PLAT-03 | Phase 13 | Complete |
| PLAT-04 | Phase 13 | Complete |
| PLAT-05 | Phase 13 | Complete |

### Phase 14 Requirements (Planned)

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXPORT-01 | Phase 14 | Planned |
| EXPORT-02 | Phase 14 | Planned |
| EXPORT-03 | Phase 14 | Planned |
| EXPORT-04 | Phase 14 | Planned |

**Coverage:**
- v1 requirements: 34 total (Complete)
- v1.1 requirements: 14 total (Complete)
- v1.2 requirements: 13 total (Complete)
- v1.3 requirements: 14 total (Complete)
- Mapped to phases: 14
- Unmapped: 0

---
*Roadmap created: 2026-04-18*
*Roadmap updated: 2026-06-08 - Milestone v1.3 (LAN Casting Support) complete*
*Roadmap updated: 2026-06-13 - Phase 14 (Static Export) planned: 5 plans across 5 waves*