# Phase 2: Bookmark Fetch and Storage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 02-bookmark-fetch-and-storage
**Mode:** Auto (--auto flag)
**Areas discussed:** Posts schema, Incremental sync, Rate limit UX, Sync output, API client architecture

---

## Posts Table Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | id, text, author_id only | |
| Standard | + created_at, media_urls, links, bookmark metadata | ✓ |
| Full | + metrics, reply_to, quote_of, extra fields | |

**User's choice:** Standard schema (auto-selected as recommended)
**Notes:** Includes all data needed for scheduling and display per DATA-02, DATA-03. X API has 800 bookmark limit so rich schema is acceptable.

---

## Incremental Sync Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full re-fetch | Fetch all 800 bookmarks every time | |
| Compare bookmark IDs | Store highest ID, fetch only newer | ✓ |
| Use timestamp | Compare bookmark.created_at | |

**User's choice:** Compare bookmark IDs (auto-selected as recommended)
**Notes:** Most reliable approach — store highest bookmark ID from last sync, fetch only newer bookmarks. Timestamp comparison has clock skew issues.

---

## Rate Limit Handling UX

| Option | Description | Selected |
|--------|-------------|----------|
| Fail with message | Stop sync, display error, user must retry | |
| Auto-wait with progress | Countdown, auto-resume when window resets | ✓ |
| Save state, prompt later | Stop sync, offer "continue later" option | |

**User's choice:** Auto-wait with progress bar (auto-selected as recommended)
**Notes:** X API allows 180 requests/15min. Show countdown, auto-resume when window resets. Better UX than failing.

---

## Sync Command Output

| Option | Description | Selected |
|--------|-------------|----------|
| Silent | Errors only | |
| Progress bar only | Live progress, no summary | |
| Progress bar + summary | Progress during, Rich table after | ✓ |

**User's choice:** Progress bar during + Rich summary table after (auto-selected as recommended)
**Notes:** Satisfies CLI-05: rich output with post content, images, metadata. Summary shows counts and sample posts.

---

## API Client Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| Direct tweepy in service | Call tweepy directly from sync service | |
| Repository pattern | Repository wraps tweepy calls | |
| Dedicated API client | Separate api/x_client.py module | ✓ |

**User's choice:** Dedicated API client module (auto-selected as recommended)
**Notes:** Research recommends `api/x_client.py` as wrapper around tweepy with rate limiting and pagination state management.

---

## Claude's Discretion

- Exact column types and constraints (TEXT vs JSON for media arrays)
- Error message wording for sync failures
- Progress bar styling (Rich Progress component choice)
- Pagination batch size

## Deferred Ideas

None — discussion stayed within phase scope.