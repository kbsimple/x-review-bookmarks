# X Bookmarked Posts Organizer

## What This Is

A Python CLI application that fetches bookmarked posts from X (Twitter) using the X Developer API, stores them in SQLite as persistent storage and cache, then organizes them into topics for scheduled resurfacing. The resurfacing follows an exponential backoff schedule based on time since publication, keeping valuable content fresh in memory.

## Core Value

Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind — content you saved because it mattered, delivered back to you before you forget it.

## Requirements

### Validated

Milestone 1 delivered:
- ✓ OAuth 2.0 PKCE authentication with X API
- ✓ SQLite storage with WAL mode (posts, tags, topics, review state)
- ✓ Bookmark sync with incremental updates and rate limit handling
- ✓ FTS5 full-text search across post content and authors
- ✓ Personal notes attached to posts
- ✓ JSON/CSV export and import
- ✓ Tags and topic taxonomy with hybrid AI suggestions
- ✓ FSRS-based spaced repetition scheduling
- ✓ Interactive review sessions via CLI

#### Validated

Milestone 2 delivered:
- ✓ FastAPI web application running locally with HTTPS
- ✓ Shared authentication with CLI (same OAuth 2.0 tokens)
- ✓ Browse posts with cursor-based pagination
- ✓ Search and filter posts (FTS5, topic, author, date range)
- ✓ Google Cast integration for Chromecast/Smart TV viewing

### Active

Milestone v1.2 — Enhanced Post Rendering:
- [ ] Store embedded post data during sync (retweets and quote tweets)
- [ ] Web app renders embedded posts with nested original content
- [ ] Cast receiver displays embedded posts on TV
- [ ] CLI renders embedded posts in terminal output

### Out of Scope

- Thread context — only individual bookmarked posts, not conversation threads
- Real-time sync — scheduled fetches are sufficient
- Mobile native app — web app with casting as fallback
- Cloud hosting — local-only deployment

## Context

**Background:** The user bookmarks posts on X that they find valuable. Over time, these bookmarks accumulate without a mechanism to revisit them. The goal is to transform bookmarks from a "save and forget" pattern into an active review system.

**Technical context:** Milestone 1 complete with OAuth 2.0 PKCE, SQLite storage, FTS5 search, topic clustering, and FSRS-based spaced repetition. All core CLI functionality is working.

**Scale:** 100-500 bookmarks across 20-30 topics.

**Milestones:**
- **Milestone 1 (v1.0):** CLI + SQLite — COMPLETE
- **Milestone 2 (v1.1):** Web App with Casting — IN PROGRESS

## Constraints

- **Tech Stack:** Python (matching existing project pattern)
- **API Access:** X Developer API credentials available (OAuth 2.0 PKCE)
- **Data Model:** Posts stored with text, author, images, links, media; no thread context required
- **Output:** Samsung Smart TV app (primary), web app with casting (fallback)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid topic model | Balance control with discovery | — Pending |
| Exponential backoff resurfacing | Spaced repetition keeps content fresh | — Pending |
| SQLite for storage | Local-first, no infrastructure, good for 100-500 scale | — Pending |
| Samsung TV as primary target | Matches user's viewing context | — Pending |

---
*Last updated: 2026-06-04 after Milestone 2 completion*

## Current Milestone: v1.2 Enhanced Post Rendering

**Goal:** Render embedded posts (retweets and quote tweets) with full original content across all display surfaces.

**Target features:**
- Expand sync to store embedded post data from X API
- Web app renders retweets/quote tweets with nested original post
- Cast receiver displays embedded posts on TV
- CLI renders embedded posts in terminal output

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state