# X Bookmarked Posts Organizer

## What This Is

A Python CLI application that fetches bookmarked posts from X (Twitter) using the X Developer API, stores them in SQLite, and organizes them for scheduled resurfacing using FSRS-based spaced repetition. Also exports a self-contained static web app deployable to Netlify — with stream/carousel presentation modes, shareable deep link URLs per post, and optional native X widget rendering via the oEmbed API.

## Core Value

Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind — content you saved because it mattered, delivered back to you before you forget it.

## Current State

**Shipped:** v1.7 (2026-06-14)
**Codebase:** ~12,000 LOC Python
**Tests:** 644 passing
**Live:** https://xbm-viewer-export.netlify.app

## Requirements

### Validated

Milestone v1.0 delivered:
- ✓ OAuth 2.0 PKCE authentication with X API — v1.0
- ✓ SQLite storage with WAL mode (posts, tags, topics, review state) — v1.0
- ✓ Bookmark sync with incremental updates and rate limit handling — v1.0
- ✓ FTS5 full-text search across post content and authors — v1.0
- ✓ Personal notes attached to posts — v1.0
- ✓ JSON/CSV export and import — v1.0
- ✓ Tags and topic taxonomy with hybrid AI suggestions — v1.0
- ✓ FSRS-based spaced repetition scheduling — v1.0
- ✓ Interactive review sessions via CLI — v1.0

Milestone v1.1 delivered:
- ✓ FastAPI web application running locally with HTTPS — v1.1
- ✓ Shared authentication with CLI (same OAuth 2.0 tokens) — v1.1
- ✓ Browse posts with cursor-based pagination — v1.1
- ✓ Search and filter posts (FTS5, topic, author, date range) — v1.1
- ✓ Google Cast integration for Chromecast/Smart TV viewing — v1.1

Milestone v1.2 delivered:
- ✓ Embedded post data stored during sync (retweets and quote tweets) — v1.2
- ✓ Web app renders embedded posts with nested original content — v1.2
- ✓ Cast receiver displays embedded posts on TV — v1.2
- ✓ CLI renders embedded posts in terminal output — v1.2

Milestone v1.3 delivered:
- ✓ Generate locally-trusted SSL certificates for LAN access (mkcert) — v1.3
- ✓ CLI command to check/generate/guide certificates — v1.3
- ✓ Web server binds to LAN IP with proper certificate — v1.3
- ✓ Mobile browser can access and cast to TV — v1.3

Milestone v1.4 delivered:
- ✓ `xbm export-static` exports bookmarks to static JSON + viewer HTML — v1.4
- ✓ Self-contained `index.html` viewer with dark theme, search, filters, sort — v1.4
- ✓ netlify-deploy skill for one-command deploy to Netlify — v1.4
- ✓ Static viewer live at https://xbm-viewer-export.netlify.app — v1.4

Milestone v1.5 delivered:
- ✓ `xbm export-static --rich-embeds` fetches and stores native oEmbed HTML — v1.5
- ✓ Static viewer renders oEmbed posts as native Twitter widgets (CDN) — v1.5
- ✓ Deleted/protected posts fall back to custom card layout — v1.5
- ✓ netlify-deploy skill updated with "deploy with rich embeds" trigger — v1.5

Milestone v1.6 delivered:
- ✓ Mode switcher (Stream / Carousel) in viewer header — v1.6
- ✓ Stream mode: existing scrollable vertical list (default, unchanged) — v1.6
- ✓ Carousel mode: one post at a time with prev/next navigation and keyboard arrow keys — v1.6
- ✓ Active mode persists across search/filter changes — v1.6
- ✓ Both modes work with oEmbed rich embeds — v1.6

Milestone v1.7 delivered:
- ✓ Share icon (📤) on every post card copies `#post-{id}` URL to clipboard with visual confirmation — v1.7
- ✓ Opening `#post-{id}` URL opens viewer in carousel mode, filters cleared, that post shown — v1.7
- ✓ Header shows "XBM Home" button (replacing mode switcher) when arrived via deep link — v1.7
- ✓ "XBM Home" navigates to root URL (full viewer, no filters) — v1.7
- ✓ Post-not-found shows graceful error with "XBM Home" link — v1.7
- ✓ Share icon works on all card types including oEmbed rich embeds — v1.7

### Active

(No active requirements — all planned features complete. Start next milestone to define new requirements.)

### Out of Scope

- Thread context — only individual bookmarked posts, not conversation threads
- Real-time sync — scheduled fetches are sufficient
- Mobile native app — web app with casting is the mobile strategy
- Cloud server — local CLI + static export covers the use case

## Context

**Background:** The user bookmarks posts on X that they find valuable. Over time, these bookmarks accumulate without a mechanism to revisit them. The goal is to transform bookmarks from a "save and forget" pattern into an active review system.

**Technical context:** All 17 phases across 8 milestones complete. Full CLI, web app, Cast integration, LAN access, static export with carousel/stream modes, deep linking, and rich embed support. 644 tests passing.

**Scale:** 100-500 bookmarks across 20-30 topics.

**Milestones:**
- **v1.0:** CLI + SQLite — COMPLETE (Phases 1–5)
- **v1.1:** Web App with Casting — COMPLETE (Phases 6–7)
- **v1.2:** Enhanced Post Rendering — COMPLETE (Phases 8–11)
- **v1.3:** LAN Casting Support — COMPLETE (Phases 12–13)
- **v1.4:** Static Export — COMPLETE (Phase 14)
- **v1.5:** oEmbed Rich Embeds — COMPLETE (Phase 15)
- **v1.6:** Viewer Presentation Modes — COMPLETE (Phase 16)
- **v1.7:** Deep Linking — COMPLETE (Phase 17)

## Constraints

- **Tech Stack:** Python (matching existing project pattern)
- **API Access:** X Developer API credentials available (OAuth 2.0 PKCE)
- **Data Model:** Posts stored with text, author, images, links, media; no thread context required
- **Output:** Samsung Smart TV app (primary), web app with casting (fallback), static Netlify export

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid topic model | Balance control with discovery | ✓ Good — AI suggestions with user approval works well |
| Exponential backoff resurfacing | Spaced repetition keeps content fresh | ✓ Good — FSRS gives flexible scheduling |
| SQLite for storage | Local-first, no infrastructure, good for 100-500 scale | ✓ Good — WAL mode handles concurrency well |
| Samsung TV as primary target | Matches user's viewing context | ✓ Good — Cast integration works |
| Static export to Netlify | Share/browse anywhere without local server | ✓ Good — free hosting, instant access |
| oEmbed with `omit_script=true` | Bare blockquote HTML + single shared CDN widget.js | ✓ Good — clean separation, one script load |
| Truthy guard `if oembed_map:` | Empty dict `{}` is falsy; prevents null injection on default path | ✓ Good — fixed critical default-path bug |
| Lazy import OEmbedService | Avoid import overhead on default export path | ✓ Good — `from .oembed import OEmbedService` inside conditional |
| Manual-only OEMBED-03 | Viewer JS is inline Python string; no JS test infra | ✓ Accepted — verified via Netlify deploy |
| CSS `body.deep-link-mode` class toggle | CSS-only mechanism to swap mode-switcher ↔ XBM Home button | ✓ Good — JS `deepLinkMode` flag is declared but inert; CSS is the actual runtime switch |
| Hash detection after `Promise.all().then()` | Ensures `allPosts` is populated before hash lookup | ✓ Good — placed after allPosts build, before renderView() |
| `goHome()` uses `origin + pathname` | Deliberately excludes fragment to clear deep-link state on navigation | ✓ Good — clean URL, no stale hash on return |
| `esc(postId)` in `showDeepLinkError()` | XSS prevention even though post IDs are currently numeric | ✓ Good — defensive convention, no harm |
| Global CSS placement (before `@media`) | Deep-link rules must apply on desktop too, not only mobile | ✓ Good — WR-01 bug caught in code review; fixed before shipping |

---
*Last updated: 2026-06-14 after v1.7 milestone*
