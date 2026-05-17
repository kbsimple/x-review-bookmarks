# Requirements: X Bookmarked Posts Organizer

**Defined:** 2026-04-18
**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind

## v1 Requirements

Requirements for initial release (Milestone 1). Each maps to roadmap phases.

### Authentication

- [x] **AUTH-01**: User can authenticate with X via OAuth 2.0 PKCE flow
- [x] **AUTH-02**: Application stores and refreshes access tokens securely
- [x] **AUTH-03**: Application handles token expiration gracefully

### Data Collection

- [ ] **DATA-01**: Application fetches bookmarked posts from X API for authenticated user
- [ ] **DATA-02**: Application stores posts with full content (text, author, images, links, media)
- [ ] **DATA-03**: Application stores publication date for each post (required for scheduling)
- [ ] **DATA-04**: Application handles X API rate limits (180 requests/15min) with resumable pagination
- [ ] **DATA-05**: Application handles the 800 bookmark API limit gracefully

### Storage

- [x] **STOR-01**: Application stores posts in SQLite database with WAL mode enabled
- [x] **STOR-02**: Application enables foreign key constraints on database connections
- [ ] **STOR-03**: Application provides incremental sync (only fetch new bookmarks since last sync)

### Search

- [ ] **SRCH-01**: User can search within stored post content (full-text search)
- [ ] **SRCH-02**: User can search by author name or username
- [ ] **SRCH-03**: Search results display relevant post content with context

### Organization

- [x] **ORG-01**: User can assign tags to bookmarked posts
- [x] **ORG-02**: User can create and manage a predefined topic taxonomy
- [ ] **ORG-03**: Application clusters posts into topics using hybrid approach (predefined + AI-suggested)
- [x] **ORG-04**: User can review and approve AI-suggested topic assignments

### Notes

- [ ] **NOTE-01**: User can add personal notes to bookmarked posts
- [ ] **NOTE-02**: Notes are displayed when post is resurfaced for review

### Spaced Repetition

- [ ] **SPAC-01**: Application calculates next review date using exponential backoff from publication date
- [ ] **SPAC-02**: Application surfaces posts for review based on calculated schedule
- [ ] **SPAC-03**: User can view currently due posts via CLI
- [ ] **SPAC-04**: Application supports themed reviews (posts from specific topics)

### CLI Interface

- [ ] **CLI-01**: User can trigger bookmark sync via CLI command
- [ ] **CLI-02**: User can view resurfaced posts via CLI command
- [ ] **CLI-03**: User can search stored posts via CLI command
- [ ] **CLI-04**: User can manage tags and topics via CLI commands
- [ ] **CLI-05**: CLI displays rich output with post content, images, and metadata

### Import/Export

- [ ] **IMEX-01**: User can export stored posts to JSON format
- [ ] **IMEX-02**: User can export stored posts to CSV format
- [ ] **IMEX-03**: User can import posts from JSON export

### Maintenance

- [ ] **MAINT-01**: Application detects and flags dead links in stored posts
- [ ] **MAINT-02**: Application can filter dead links from review queue

## v1.1 Requirements

Requirements for Milestone 2 (Web App with Casting). Each maps to roadmap phases.

### Web Foundation

- [ ] **WEB-01**: User can access application via web browser at localhost
- [ ] **WEB-02**: Web app serves posts over HTTPS (required for Google Cast)
- [ ] **WEB-03**: Web app authenticates using shared CLI tokens (data/tokens.json)
- [ ] **WEB-04**: User can browse posts with cursor-based pagination
- [ ] **WEB-05**: User can search posts by text content (FTS5)
- [ ] **WEB-06**: User can filter posts by topic, author, date range

### Cast Integration

- [ ] **CAST-01**: User sees Cast button in web app header
- [ ] **CAST-02**: User can connect to Chromecast/Smart TV devices
- [ ] **CAST-03**: User can cast post content to TV screen
- [ ] **CAST-04**: Mini controller displays during active cast session
- [ ] **CAST-05**: Cast session state persists across navigation

### Custom Web Receiver

- [ ] **RCVR-01**: Custom Web Receiver displays post text and images on TV
- [ ] **RCVR-02**: Receiver handles post content loading from web app
- [ ] **RCVR-03**: Receiver displays post author and publication date

## v2 Requirements

Deferred to future release (Milestone 2/3). Tracked but not in current roadmap.

### Enhanced Display

- **DISP-01**: Web application for viewing resurfaced posts (fallback for Samsung TV)
- **DISP-02**: Samsung TV native application for passive viewing
- **DISP-03**: Mobile-responsive web interface

### Enhanced Clustering

- **CLUS-01**: Advanced AI topic suggestions using local LLM
- **CLUS-02**: Automatic topic discovery without predefined taxonomy
- **CLUS-03**: Topic merge and split operations

### Integration

- **INTG-01**: Readwise export integration
- **INTG-02**: Notion export integration
- **INTG-03**: Obsidian vault sync

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Complex folder hierarchies | Causes decision fatigue; flat tags + search-first is better |
| "Read Later" queue | Becomes digital landfill; spaced repetition removes this need |
| Real-time sync | Overkill for 100-500 bookmark scale; scheduled sync sufficient |
| Manual scheduling | Adds decision fatigue; algorithm handles this automatically |
| Social features (sharing, feed) | Distraction from core value (personal retention) |
| AI-generated summaries | Removes insight/discovery that makes content valuable |
| Unlimited storage scale | 100-500 is manageable; more becomes unmanageable |
| Thread context | Only individual bookmarked posts, not conversation threads |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

### v1 Requirements (Complete)

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

### v1.1 Requirements (Pending)

| Requirement | Phase | Status |
|-------------|-------|--------|
| WEB-01 | Phase 6 | Pending |
| WEB-02 | Phase 6 | Pending |
| WEB-03 | Phase 6 | Pending |
| WEB-04 | Phase 6 | Pending |
| WEB-05 | Phase 6 | Pending |
| WEB-06 | Phase 6 | Pending |
| CAST-01 | Phase 7 | Pending |
| CAST-02 | Phase 7 | Pending |
| CAST-03 | Phase 7 | Pending |
| CAST-04 | Phase 7 | Pending |
| CAST-05 | Phase 7 | Pending |
| RCVR-01 | Phase 7 | Pending |
| RCVR-02 | Phase 7 | Pending |
| RCVR-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 34 total (Complete)
- v1.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-05-17 after v1.1 requirements added*