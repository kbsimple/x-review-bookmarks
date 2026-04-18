# X Bookmarked Posts Organizer

## What This Is

A Python CLI application that fetches bookmarked posts from X (Twitter) using the X Developer API, stores them in SQLite as persistent storage and cache, then organizes them into topics for scheduled resurfacing. The resurfacing follows an exponential backoff schedule based on time since publication, keeping valuable content fresh in memory.

## Core Value

Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind — content you saved because it mattered, delivered back to you before you forget it.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Fetch bookmarked posts from X API for authenticated user
- [ ] Store posts in SQLite with full content (text, author, images, links, media)
- [ ] Cluster posts into topics using hybrid approach (predefined + AI-suggested)
- [ ] Resurface posts on exponential backoff schedule based on publication date
- [ ] View resurfaced posts on Samsung Smart TV

### Out of Scope

- Thread context — only individual bookmarked posts, not conversation threads
- Real-time sync — scheduled fetches are sufficient
- Mobile native app — web app with casting as fallback

## Context

**Background:** The user bookmarks posts on X that they find valuable. Over time, these bookmarks accumulate without a mechanism to revisit them. The goal is to transform bookmarks from a "save and forget" pattern into an active review system.

**Technical context:** Auth pattern from existing project (kbsimple/X-follow-clusters) will be reused — OAuth 2.0 PKCE with tweepy.

**Scale:** 100-500 bookmarks across 20-30 topics.

**Milestones:**
- **Milestone 1:** CLI + SQLite — fetch and store bookmarked posts
- **Milestone 2:** Topic clustering — hybrid model (predefined + AI-suggested topics)
- **Milestone 3:** Delivery — scheduled resurfacing with Samsung TV viewing

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
*Last updated: 2026-04-18 after initialization*

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