# Project Research Summary

**Project:** x-bookmarked-posts
**Domain:** Python CLI application for X/Twitter API bookmark management with spaced repetition resurfacing
**Researched:** 2026-04-18
**Confidence:** HIGH

## Executive Summary

This is a local-first Python CLI application that fetches bookmarked posts from X (Twitter), organizes them with topic clustering, and resurfaces content using spaced repetition algorithms. Experts in this domain combine three established patterns: (1) OAuth 2.0 PKCE authentication for social media APIs, (2) repository-pattern data access with SQLite for local storage, and (3) FSRS/SM-2 algorithms for spaced repetition scheduling. The recommended architecture follows a clean three-layer separation: CLI commands (Typer), service orchestration, and repository-based data access.

The primary technical risks center on X API constraints: the bookmarks endpoint requires OAuth 2.0 User Context (not app-only auth), there is a hard limit of 800 retrievable bookmarks, and rate limits demand careful pagination state management. These must be addressed in the foundation phase to avoid data loss or failed syncs. The core product differentiator---spaced repetition resurfacing---is well-documented in the learning science literature and should use the FSRS algorithm (py-fsrs library) rather than the older SM-2 to avoid "ease hell" where review intervals spiral downward.

## Key Findings

### Recommended Stack

The research indicates a mature, well-documented Python stack. Typer provides type-hint-based CLI with minimal boilerplate, Rich handles terminal output with tables and progress bars, and Tweepy is the only maintained Python library for X API v2. SQLite with WAL mode is ideal for the 100-500 bookmark scale, requiring no additional infrastructure.

**Core technologies:**
- **Python 3.10+**: Required for modern type hints (Typer) and pattern matching
- **Typer 0.24+**: CLI framework with built-in shell completion and Rich integration
- **Tweepy 4.16+**: Only mature X API v2 client with OAuth 2.0 PKCE support
- **SQLite with WAL**: Zero-config local storage, thread-safe with proper configuration
- **APScheduler 3.11+**: In-process scheduling for resurfacing jobs
- **py-fsrs**: Spaced repetition algorithm (preferred over SM-2)
- **Pydantic Settings 2.0+**: Type-safe configuration from environment variables

### Expected Features

**Must have (table stakes):**
- Full-text search within bookmark content (not just titles/URLs)
- Tag/folder organization with hybrid approach (tags + collections)
- Import/export functionality (JSON/CSV minimum)
- Fast sync (sub-2-second capture)
- Visual previews with author context

**Should have (competitive):**
- Spaced repetition resurfacing --- core differentiator, transforms "save and forget" into "retain and apply"
- Hybrid topic clustering --- predefined topics for known interests + AI suggestions for discovery
- Algorithm-based scheduling --- publication date + spaced repetition = predictable review cadence
- Notes attached to bookmarks --- context for why saved

**Defer (v2+):**
- Samsung TV native app --- high complexity, requires Tizen development
- Readwise/Notion export integration --- ecosystem connection
- Mobile capture app --- X native bookmarks currently sufficient

**Anti-features to avoid:**
- Complex folder hierarchies (causes "folder paralysis")
- "Read Later" queue (becomes digital landfill)
- AI-generated summaries (removes insight/discovery value)
- Manual scheduling (adds decision fatigue)

### Architecture Approach

The research recommends a standard three-layer architecture: CLI layer (Typer commands) calls service layer (business logic orchestration) which uses repository layer (data access abstraction). This pattern is well-documented and enables clean testing with mock repositories.

**Major components:**
1. **CLI Layer** (cli.py) --- Typer commands for fetch, topics, resurface; Rich for output formatting
2. **Service Layer** (services/) --- FetchService, TopicService, SchedulerService orchestrate business logic
3. **Repository Layer** (repositories/) --- SQLitePostRepository, TopicRepository, ScheduleRepository abstract SQL
4. **X API Client** (api/x_client.py) --- Tweepy wrapper with rate limiting and pagination
5. **Auth Module** (auth/oauth.py) --- OAuth 2.0 PKCE flow handler
6. **Scheduler** (scheduler/fsrs_wrapper.py) --- FSRS algorithm integration

Key architectural patterns: dependency injection container (dependency-injector library), thread-local SQLite connections with WAL mode, repository pattern for testability.

### Critical Pitfalls

1. **X API 403 Forbidden** --- Bookmarks endpoint requires OAuth 2.0 User Context with PKCE, NOT app-only Bearer Token. Use tweepy.OAuth2UserHandler, not OAuth2AppHandler.

2. **800 Bookmark Retrieval Limit** --- X API only returns the 800 most recent bookmarks. Document clearly, implement incremental sync before bookmarks age out.

3. **Rate Limit Exhaustion** --- X API allows 180 requests/15 min for bookmarks. Store `next_token` in SQLite to resume pagination after interruptions.

4. **SQLite Foreign Key Violations** --- FK enforcement is DISABLED by default. Must call `PRAGMA foreign_keys = ON` on every connection.

5. **SM-2 "Ease Hell"** --- Classic algorithm causes review intervals to spiral downward. Use FSRS algorithm instead, or implement ease factor minimum caps.

## Implications for Roadmap

Based on dependency analysis and pitfall mapping, recommended phase structure:

### Phase 1: Foundation and Authentication
**Rationale:** Authentication and database setup are prerequisites for all other work. X API PKCE flow is the most common failure point.
**Delivers:** Working auth flow, SQLite schema, repository interfaces
**Addresses:** Feature dependency (fetch requires auth)
**Avoids:** Pitfalls 1 (403 Forbidden), 4 (FK violations), 6 (rate limits)
**Stack:** Python 3.10+, Typer, SQLite, pydantic-settings

### Phase 2: Bookmark Fetch and Storage
**Rationale:** Core data flow must work before any features can be built on it.
**Delivers:** CLI fetch command, X API integration, post storage
**Addresses:** Table stakes (fast sync, import/export foundation)
**Avoids:** Pitfalls 2 (800 limit --- document clearly), 3 (rate limits --- implement resume)
**Stack:** Tweepy, repository pattern

### Phase 3: Topic Clustering
**Rationale:** Requires stored posts to cluster. Enhances spaced repetition with themed reviews.
**Delivers:** Topic taxonomy, clustering service, topic assignment
**Addresses:** Differentiator (hybrid topic clustering)
**Avoids:** Pitfall 5 (semantic drift --- store embeddings with metadata)
**Stack:** sentence-transformers, scikit-learn (optional dependencies)

### Phase 4: Spaced Repetition Scheduling
**Rationale:** Core differentiator, requires posts and topics for themed reviews.
**Delivers:** FSRS integration, schedule repository, resurface CLI command
**Addresses:** Core differentiator (algorithm-based scheduling)
**Avoids:** Pitfall 4 (ease hell --- use FSRS not SM-2)
**Stack:** py-fsrs, APScheduler

### Phase 5: Enhanced Display
**Rationale:** Final output layer, can iterate after core functionality works.
**Delivers:** Rich CLI output, notes on bookmarks, themed review display
**Addresses:** Table stakes (visual previews, notes feature)
**Stack:** Rich, existing services

### Phase Ordering Rationale

- **Phase 1 first:** OAuth 2.0 PKCE is the most critical and commonly broken integration. Get it working before anything else.
- **Phase 2 second:** Must fetch and store data before clustering or scheduling can work.
- **Phase 3 third:** Topic clustering enhances spaced repetition (themed reviews) but is optional for MVP.
- **Phase 4 fourth:** Spaced repetition scheduling is the core differentiator, requires posts + topics.
- **Phase 5 last:** Display enhancements are iterative polish, not blockers.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4:** FSRS integration details may need spike (py-fsrs library usage patterns)
- **Phase 3:** Topic clustering model selection (all-MiniLM-L6-v2 vs alternatives)

Phases with standard patterns (skip research-phase):
- **Phase 1:** OAuth 2.0 PKCE is well-documented, existing x-api project has working pattern
- **Phase 2:** Tweepy usage is standard, repository pattern is well-established
- **Phase 5:** Rich CLI output is straightforward, well-documented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies are mature with official documentation. Typer, Tweepy, SQLite patterns are well-established. |
| Features | HIGH | Multiple bookmark manager products analyzed. Spaced repetition algorithms (FSRS, SM-2) have extensive literature. |
| Architecture | HIGH | Repository pattern and dependency injection are standard Python CLI patterns. Multiple authoritative sources confirm. |
| Pitfalls | HIGH | X API constraints documented officially. SQLite gotchas are well-known. FSRS/SM-2 issues documented in learning science literature. |

**Overall confidence:** HIGH

### Gaps to Address

- **Samsung TV delivery:** Research focused on CLI. If TV app becomes priority, need Tizen/web app research. Current plan is CLI MVP with TV as future consideration.
- **Embedding model selection:** all-MiniLM-L6-v2 is recommended but benchmark comparison with alternatives would strengthen choice. Can spike during Phase 3.
- **Topic taxonomy seed data:** Research mentions "predefined topic taxonomy" but does not specify categories. Will need user input during planning.

## Sources

### Primary (HIGH confidence)
- Typer Documentation --- CLI framework patterns
- Tweepy Documentation --- X API integration, OAuth 2.0 PKCE
- X API Bookmarks Documentation --- endpoint requirements, rate limits
- py-fsrs GitHub --- Spaced repetition algorithm implementation
- SQLite WAL Mode Best Practices --- performance configuration

### Secondary (MEDIUM confidence)
- Python CLI Architecture Guide --- service layer patterns
- Repository Pattern for SQLite --- data access abstraction
- FSRS Algorithm Explanation (Domenic) --- spaced repetition science
- BetterStacks Bookmark Manager Features --- feature landscape analysis

### Tertiary (LOW confidence)
- Social Media Database Schema Example --- schema inspiration (adapted to needs)
- Community blog posts on SQLite gotchas --- validated against official docs

### Project Reference
- Existing x-api project --- OAuth 2.0 PKCE implementation pattern (auth/x_auth.py)

---
*Research completed: 2026-04-18*
*Ready for roadmap: yes*
